/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect, Layer, Ref, Duration, TestClock } from "effect";
import { HttpClient, HttpClientResponse } from "@effect/platform";

import { makeHttpClientLayer } from "@/services/http-client";
import { HttpClientRegistry } from "@/services/http-client";

describe("HttpClientLayer Caching", () => {
  it.effect(
    "should cache GET requests and serve cached response on repeated calls",
    () =>
      Effect.gen(function* () {
        const callCountRef = yield* Ref.make(0);

        const mockExtClient = HttpClient.make((request) =>
          Effect.gen(function* () {
            yield* Ref.update(callCountRef, (n) => n + 1);
            return HttpClientResponse.fromWeb(
              request,
              new Response(JSON.stringify({ ok: true }), {
                status: 200,
                headers: { "content-type": "application/json" },
              }),
            );
          }),
        );

        const MockRegistryLayer = Layer.succeed(HttpClientRegistry, {
          getAvailableExtensions: Effect.succeed([]),
          getClient: () => Effect.succeed(mockExtClient),
        });

        const client = yield* HttpClient.HttpClient.pipe(
          Effect.provide(
            makeHttpClientLayer({
              capacity: 10,
              timeToLive: Duration.seconds(5),
            }),
          ),
          Effect.provide(MockRegistryLayer),
        );

        const res1 = yield* client.get("one-extension://service/users");
        const json1 = yield* res1.json;
        expect(json1).toEqual({ ok: true });

        const res2 = yield* client.get("one-extension://service/users");
        const json2 = yield* res2.json;
        expect(json2).toEqual({ ok: true });

        const totalCalls = yield* Ref.get(callCountRef);
        expect(totalCalls).toBe(1);
      }),
  );

  it.effect(
    "should invalidate cache when a mutation (POST/PUT/DELETE) is executed",
    () =>
      Effect.gen(function* () {
        const callCountRef = yield* Ref.make(0);

        const mockExtClient = HttpClient.make((request) =>
          Effect.gen(function* () {
            yield* Ref.update(callCountRef, (n) => n + 1);
            return HttpClientResponse.fromWeb(
              request,
              new Response(
                JSON.stringify({ count: yield* Ref.get(callCountRef) }),
                {
                  status: 200,
                  headers: { "content-type": "application/json" },
                },
              ),
            );
          }),
        );

        const MockRegistryLayer = Layer.succeed(HttpClientRegistry, {
          getAvailableExtensions: Effect.succeed([]),
          getClient: () => Effect.succeed(mockExtClient),
        });

        const client = yield* HttpClient.HttpClient.pipe(
          Effect.provide(
            makeHttpClientLayer({
              capacity: 10,
              timeToLive: Duration.seconds(5),
            }),
          ),
          Effect.provide(MockRegistryLayer),
        );

        yield* client.get("one-extension://service/items");
        yield* client.get("one-extension://service/items");
        expect(yield* Ref.get(callCountRef)).toBe(1);

        yield* client.post("one-extension://service/items");
        expect(yield* Ref.get(callCountRef)).toBe(2);

        yield* client.get("one-extension://service/items");
        expect(yield* Ref.get(callCountRef)).toBe(3);
      }),
  );

  it.effect("should expire cache entries after TTL", () =>
    Effect.gen(function* () {
      const callCountRef = yield* Ref.make(0);

      const mockExtClient = HttpClient.make((request) =>
        Effect.gen(function* () {
          yield* Ref.update(callCountRef, (n) => n + 1);
          return HttpClientResponse.fromWeb(
            request,
            new Response(
              JSON.stringify({ value: yield* Ref.get(callCountRef) }),
              {
                status: 200,
                headers: { "content-type": "application/json" },
              },
            ),
          );
        }),
      );

      const MockRegistryLayer = Layer.succeed(HttpClientRegistry, {
        getAvailableExtensions: Effect.succeed([]),
        getClient: () => Effect.succeed(mockExtClient),
      });

      const client = yield* HttpClient.HttpClient.pipe(
        Effect.provide(
          makeHttpClientLayer({
            capacity: 10,
            timeToLive: Duration.seconds(10),
          }),
        ),
        Effect.provide(MockRegistryLayer),
      );

      yield* client.get("one-extension://service/data");
      expect(yield* Ref.get(callCountRef)).toBe(1);

      yield* TestClock.adjust(Duration.seconds(5));
      yield* client.get("one-extension://service/data");
      expect(yield* Ref.get(callCountRef)).toBe(1);

      yield* TestClock.adjust(Duration.seconds(6));
      yield* client.get("one-extension://service/data");
      expect(yield* Ref.get(callCountRef)).toBe(2);
    }),
  );

  it.effect(
    "should isolate cache entries for different Authorization headers",
    () =>
      Effect.gen(function* () {
        const callCountRef = yield* Ref.make(0);

        const mockExtClient = HttpClient.make((request) =>
          Effect.gen(function* () {
            yield* Ref.update(callCountRef, (n) => n + 1);
            const auth = request.headers["authorization"] ?? "none";
            return HttpClientResponse.fromWeb(
              request,
              new Response(JSON.stringify({ user: auth }), {
                status: 200,
                headers: { "content-type": "application/json" },
              }),
            );
          }),
        );

        const MockRegistryLayer = Layer.succeed(HttpClientRegistry, {
          getAvailableExtensions: Effect.succeed([]),
          getClient: () => Effect.succeed(mockExtClient),
        });

        const client = yield* HttpClient.HttpClient.pipe(
          Effect.provide(
            makeHttpClientLayer({
              capacity: 10,
              timeToLive: Duration.seconds(5),
            }),
          ),
          Effect.provide(MockRegistryLayer),
        );

        // 1. First call with Alice's token -> Cache MISS
        const resAlice1 = yield* client.get("one-extension://service/me", {
          headers: { authorization: "Bearer alice-token" },
        });
        expect(yield* resAlice1.json).toEqual({ user: "Bearer alice-token" });
        expect(yield* Ref.get(callCountRef)).toBe(1);

        // 2. Second call with Alice's token -> Cache HIT
        const resAlice2 = yield* client.get("one-extension://service/me", {
          headers: { authorization: "Bearer alice-token" },
        });
        expect(yield* resAlice2.json).toEqual({ user: "Bearer alice-token" });
        expect(yield* Ref.get(callCountRef)).toBe(1);

        // 3. Same URL with Bob's token -> Cache MISS (distinct entry)
        const resBob = yield* client.get("one-extension://service/me", {
          headers: { authorization: "Bearer bob-token" },
        });
        expect(yield* resBob.json).toEqual({ user: "Bearer bob-token" });
        expect(yield* Ref.get(callCountRef)).toBe(2);
      }),
  );

  it.effect("should not cache 4xx/5xx error responses", () =>
    Effect.gen(function* () {
      const callCountRef = yield* Ref.make(0);

      const mockExtClient = HttpClient.make((request) =>
        Effect.gen(function* () {
          const count = yield* Ref.updateAndGet(callCountRef, (n) => n + 1);
          // Returns 401 on the first call, then 200 on subsequent calls
          if (count === 1) {
            return HttpClientResponse.fromWeb(
              request,
              new Response(JSON.stringify({ error: "Unauthorized" }), {
                status: 401,
                headers: { "content-type": "application/json" },
              }),
            );
          }
          return HttpClientResponse.fromWeb(
            request,
            new Response(JSON.stringify({ ok: true }), {
              status: 200,
              headers: { "content-type": "application/json" },
            }),
          );
        }),
      );

      const MockRegistryLayer = Layer.succeed(HttpClientRegistry, {
        getAvailableExtensions: Effect.succeed([]),
        getClient: () => Effect.succeed(mockExtClient),
      });

      const client = yield* HttpClient.HttpClient.pipe(
        Effect.provide(
          makeHttpClientLayer({
            capacity: 10,
            timeToLive: Duration.seconds(5),
          }),
        ),
        Effect.provide(MockRegistryLayer),
      );

      // First call: returns 401 status
      const res1 = yield* client.get("one-extension://service/protected");
      expect(res1.status).toBe(401);
      expect(yield* Ref.get(callCountRef)).toBe(1);

      // Second immediate call: cache must be bypassed, reaching network and returning 200
      const res2 = yield* client.get("one-extension://service/protected");
      expect(res2.status).toBe(200);
      expect(yield* res2.json).toEqual({ ok: true });
      expect(yield* Ref.get(callCountRef)).toBe(2);
    }),
  );
});
