/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import fc from "fast-check";
import { Effect, Layer, Ref, Duration, TestClock, Runtime } from "effect";
import { HttpClient, HttpClientResponse } from "@effect/platform";
import { makeHttpClientLayer } from "@/services/http-client";
import { HttpClientRegistry } from "@/services/http-client";

interface CacheModel {
  currentTime: number; // in seconds
  // Key format: `${endpoint}#${authHeader}` -> { value: number, expiresAt: number }
  entries: Map<string, { value: number; expiresAt: number }>;
  totalBackendCalls: number;
}

// SUT -> System Under Test
interface SUT {
  run: <A, E>(effect: Effect.Effect<A, E, any>) => Promise<A>;
  client: HttpClient.HttpClient;
  callCountRef: Ref.Ref<number>;
}

const TTL_SECONDS = 10;

class GetCommand implements fc.AsyncCommand<CacheModel, SUT> {
  readonly endpoint: string;
  readonly token?: string;

  constructor(endpoint: string, token?: string) {
    this.endpoint = endpoint;
    this.token = token;
  }

  check(_model: Readonly<CacheModel>): boolean {
    return true;
  }

  async run(model: CacheModel, sut: SUT): Promise<void> {
    const fullUrl = `ext://service/${this.endpoint}`;
    const headers: Record<string, string> = this.token
      ? { authorization: `Bearer ${this.token}` }
      : {};

    const res = await sut.run(sut.client.get(fullUrl, { headers }));

    // An invalid token simulates a 401 Unauthorized response
    const isUnauthorized = this.token === "invalid";

    if (isUnauthorized) {
      expect(res.status).toBe(401);
      // Non-2xx error responses must never be cached; each attempt reaches the backend
      model.totalBackendCalls += 1;
      const json = (await sut.run(res.json)) as { callCount: number };
      expect(json.callCount).toBe(model.totalBackendCalls);
    } else {
      expect(res.status).toBe(200);
      const json = (await sut.run(res.json)) as {
        endpoint: string;
        callCount: number;
      };

      // The cache key partitions by endpoint and Authorization header
      const cacheKey = `${this.endpoint}#${this.token ? `Bearer ${this.token}` : ""}`;
      const existing = model.entries.get(cacheKey);
      const isHit = existing && model.currentTime <= existing.expiresAt;

      if (isHit) {
        expect(json.callCount).toBe(existing.value);
      } else {
        model.totalBackendCalls += 1;
        model.entries.set(cacheKey, {
          value: model.totalBackendCalls,
          expiresAt: model.currentTime + TTL_SECONDS,
        });
        expect(json.callCount).toBe(model.totalBackendCalls);
      }
    }

    const actualBackendCalls = await sut.run(Ref.get(sut.callCountRef));
    expect(actualBackendCalls).toBe(model.totalBackendCalls);
  }

  toString(): string {
    return `GET(${this.endpoint}, auth=${this.token ?? "anonymous"})`;
  }
}

class MutateCommand implements fc.AsyncCommand<CacheModel, SUT> {
  readonly endpoint: string;

  constructor(endpoint: string) {
    this.endpoint = endpoint;
  }

  check(_model: Readonly<CacheModel>): boolean {
    return true;
  }

  async run(model: CacheModel, sut: SUT): Promise<void> {
    const fullUrl = `ext://service/${this.endpoint}`;

    await sut.run(sut.client.post(fullUrl));

    // A mutation invalidates all cache entries across all partitions
    model.totalBackendCalls += 1;
    model.entries.clear();

    const actualBackendCalls = await sut.run(Ref.get(sut.callCountRef));
    expect(actualBackendCalls).toBe(model.totalBackendCalls);
  }

  toString(): string {
    return `POST(${this.endpoint}) [invalidation]`;
  }
}

class AdvanceTimeCommand implements fc.AsyncCommand<CacheModel, SUT> {
  readonly seconds: number;

  constructor(seconds: number) {
    this.seconds = seconds;
  }

  check(_model: Readonly<CacheModel>): boolean {
    return this.seconds > 0;
  }

  async run(model: CacheModel, sut: SUT): Promise<void> {
    model.currentTime += this.seconds;
    await sut.run(TestClock.adjust(Duration.seconds(this.seconds)));
  }

  toString(): string {
    return `ADVANCE_TIME(+${this.seconds}s)`;
  }
}

describe("HttpCache - Model-Based Testing", () => {
  it.effect(
    "conforms to reference cache model across arbitrary operation sequences",
    () =>
      Effect.gen(function* () {
        const runtime = yield* Effect.runtime<any>();
        const run = Runtime.runPromise(runtime);

        const endpointArb = fc.constantFrom(
          "users",
          "sensors",
          "alerts",
          "config",
        );

        // Generates different users, invalid credentials, and anonymous requests
        const tokenArb = fc.constantFrom(
          "alice-token",
          "bob-token",
          "invalid",
          undefined,
        );

        const commandsArb = fc.commands(
          [
            fc
              .tuple(endpointArb, tokenArb)
              .map(([ep, tok]) => new GetCommand(ep, tok)),
            endpointArb.map((ep) => new MutateCommand(ep)),
            fc
              .integer({ min: 1, max: 20 })
              .map((s) => new AdvanceTimeCommand(s)),
          ],
          { size: "medium" },
        );

        yield* Effect.promise(() =>
          fc.assert(
            fc.asyncProperty(commandsArb, async (cmds) => {
              // Reset virtual clock to 0 at start of each property run
              await run(TestClock.setTime(0));

              const callCountRef = await run(Ref.make(0));

              const mockExtClient = HttpClient.make((request) =>
                Effect.gen(function* () {
                  const count = yield* Ref.updateAndGet(
                    callCountRef,
                    (n) => n + 1,
                  );
                  const auth = request.headers["authorization"];

                  // Simulate 401 Unauthorized for invalid token
                  if (auth === "Bearer invalid") {
                    return HttpClientResponse.fromWeb(
                      request,
                      new Response(
                        JSON.stringify({
                          error: "Unauthorized",
                          callCount: count,
                        }),
                        {
                          status: 401,
                          headers: { "content-type": "application/json" },
                        },
                      ),
                    );
                  }

                  return HttpClientResponse.fromWeb(
                    request,
                    new Response(
                      JSON.stringify({
                        endpoint: request.url,
                        callCount: count,
                        user: auth ?? "anonymous",
                      }),
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

              const client = await run(
                HttpClient.HttpClient.pipe(
                  Effect.provide(
                    makeHttpClientLayer({
                      capacity: 100,
                      timeToLive: Duration.seconds(TTL_SECONDS),
                    }),
                  ),
                  Effect.provide(MockRegistryLayer),
                ),
              );

              const sut: SUT = {
                run,
                client,
                callCountRef,
              };

              const model: CacheModel = {
                currentTime: 0,
                entries: new Map(),
                totalBackendCalls: 0,
              };

              await fc.asyncModelRun(() => ({ model, real: sut }), cmds);
            }),
            { numRuns: 50 },
          ),
        );
      }),
  );
});
