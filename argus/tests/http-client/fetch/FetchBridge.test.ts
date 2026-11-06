/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect, Layer, Fiber, Ref, Cause } from "effect";
import { HttpClientResponse } from "@effect/platform";
import { Blob } from "node:buffer"

import { HttpClientRegistry } from "@/services/http-client";
import { FetchBridgeService, FetchBridgeLive } from "@/services/http-client";

const makeMockRegistry = (
  handler: (req: any) => Effect.Effect<any, any, any>,
) =>
  Layer.succeed(
    HttpClientRegistry,
    HttpClientRegistry.of({
      getAvailableExtensions: Effect.succeed([]),
      getClient: (_clientId: string) =>
        Effect.succeed({
          execute: (req: any) => handler(req),
        } as any),
    }),
  );

describe("FetchBridge - Response Native Compatibility", () => {
  const DefaultLive = FetchBridgeLive.pipe(
    Layer.provide(
      makeMockRegistry((req) =>
        Effect.succeed(
          HttpClientResponse.fromWeb(
            req,
            new Response(JSON.stringify({ ok: true, method: req.method }), {
              status: 200,
              headers: { "content-type": "application/json" },
            }),
          ),
        ),
      ),
    ),
  );

  it.effect(
    "should return a native Response conforming to standard specs",
    () =>
      Effect.gen(function* () {
        const bridge = yield* FetchBridgeService;
        const response = yield* bridge.execute("herge://api/check");

        // 1. Prototype inheritance
        expect(response instanceof Response).toBe(true);
        expect(typeof response.status).toBe("number");
        expect(response.status).toBe(200);
        expect(response.ok).toBe(true);

        // 2. Headers compliance
        expect(response.headers).toBeDefined();
        expect(typeof response.headers.get).toBe("function");
        expect(response.headers.get("content-type")).toBe("application/json");

        // 3. Clone compatibility (critical for Sentry / loggers)
        const cloned = response.clone();
        expect(cloned instanceof Response).toBe(true);

        const text1 = yield* Effect.promise(() => response.text());
        const text2 = yield* Effect.promise(() => cloned.text());
        expect(text1).toBe(text2);
        expect(JSON.parse(text1)).toEqual({ ok: true, method: "GET" });
      }).pipe(Effect.provide(DefaultLive)),
  );
});

describe("FetchBridge - BodyInit Support", () => {
  it.effect("should support URLSearchParams body", () =>
    Effect.gen(function* () {
      let capturedBody: any;
      const layer = FetchBridgeLive.pipe(
        Layer.provide(
          makeMockRegistry((req) => {
            capturedBody = req.body;
            return Effect.succeed(
              HttpClientResponse.fromWeb(
                req,
                new Response("ok", { status: 200 }),
              ),
            );
          }),
        ),
      );

      const bridge = yield* FetchBridgeService.pipe(Effect.provide(layer));
      const params = new URLSearchParams({ key: "val", test: "123" });

      const response = yield* bridge.execute("herge://api/form", {
        method: "POST",
        body: params,
      });

      expect(response.status).toBe(200);
      expect(capturedBody._tag).toBe("Uint8Array");
      const decoded = new TextDecoder().decode(capturedBody.body);
      expect(decoded).toBe("key=val&test=123");
    }),
  );

  it.effect("should support Uint8Array body", () =>
    Effect.gen(function* () {
      let capturedBody: any;
      const layer = FetchBridgeLive.pipe(
        Layer.provide(
          makeMockRegistry((req) => {
            capturedBody = req.body;
            return Effect.succeed(
              HttpClientResponse.fromWeb(
                req,
                new Response("ok", { status: 200 }),
              ),
            );
          }),
        ),
      );

      const bridge = yield* FetchBridgeService.pipe(Effect.provide(layer));
      const bytes = new Uint8Array([1, 2, 3, 4]);

      const response = yield* bridge.execute("scada://api/binary", {
        method: "POST",
        body: bytes,
      });

      expect(response.status).toBe(200);
      expect(capturedBody._tag).toBe("Uint8Array");
      expect(Array.from(capturedBody.body)).toEqual([1, 2, 3, 4]);
    }),
  );

  it.effect("should support ArrayBuffer body", () =>
    Effect.gen(function* () {
      let capturedBody: any;
      const layer = FetchBridgeLive.pipe(
        Layer.provide(
          makeMockRegistry((req) => {
            capturedBody = req.body;
            return Effect.succeed(
              HttpClientResponse.fromWeb(
                req,
                new Response("ok", { status: 200 }),
              ),
            );
          }),
        ),
      );

      const bridge = yield* FetchBridgeService.pipe(Effect.provide(layer));
      const buffer = new Uint8Array([10, 20, 30]).buffer;

      const response = yield* bridge.execute("scada://api/buffer", {
        method: "POST",
        body: buffer,
      });

      expect(response.status).toBe(200);
      expect(capturedBody._tag).toBe("Uint8Array");
      expect(Array.from(capturedBody.body)).toEqual([10, 20, 30]);
    }),
  );

  it.effect("should support Blob body", () =>
    Effect.gen(function* () {
      let capturedBody: any;
      const layer = FetchBridgeLive.pipe(
        Layer.provide(
          makeMockRegistry((req) => {
            capturedBody = req.body;
            return Effect.succeed(
              HttpClientResponse.fromWeb(
                req,
                new Response("ok", { status: 200 }),
              ),
            );
          }),
        ),
      );

      const bridge = yield* FetchBridgeService.pipe(Effect.provide(layer));
      const blob = new Blob(["blob payload"], { type: "text/plain" });

      const response = yield* bridge.execute("scada://api/blob", {
        method: "POST",
        body: blob as any,
      });

      expect(response.status).toBe(200);
      expect(capturedBody._tag).toBe("Uint8Array");
      const decoded = new TextDecoder().decode(capturedBody.body);
      expect(decoded).toBe("blob payload");
    }),
  );
});

describe("FetchBridge - AbortController Lifecycle", () => {
  it.effect(
    "should reject with DOMException(AbortError) if already aborted prior to call",
    () =>
      Effect.gen(function* () {
        const layer = FetchBridgeLive.pipe(
          Layer.provide(
            makeMockRegistry((req) =>
              Effect.succeed(
                HttpClientResponse.fromWeb(
                  req,
                  new Response("ok", { status: 200 }),
                ),
              ),
            ),
          ),
        );

        const bridge = yield* FetchBridgeService.pipe(Effect.provide(layer));
        const controller = new AbortController();
        controller.abort();

        const exit = yield* Effect.exit(
          bridge.execute("herge://api/aborted", { signal: controller.signal }),
        );

        expect(exit._tag).toBe("Failure");
        if (exit._tag === "Failure") {
          const error = Cause.squash(exit.cause) as DOMException;
          expect(error).toBeInstanceOf(DOMException);
          expect(error.name).toBe("AbortError");
        }

      }),
  );

  it.effect(
    "should interrupt underlying effect and reject when signal is triggered in-flight",
    () =>
      Effect.gen(function* () {
        const interruptedRef = yield* Ref.make(false);
        const startedRef = yield* Ref.make(false);

        const layer = FetchBridgeLive.pipe(
          Layer.provide(
            makeMockRegistry((_req) =>
              Ref.set(startedRef, true).pipe(
                Effect.zipRight(Effect.never),
                Effect.onInterrupt(() => Ref.set(interruptedRef, true)),
              ),
            ),
          ),
        );

        const bridge = yield* FetchBridgeService.pipe(Effect.provide(layer));
        const controller = new AbortController();

        const fiber = yield* Effect.fork(
          bridge.execute("herge://api/slow", { signal: controller.signal }),
        );

        // Determinist waiting for request in client mock
        yield* Effect.repeat(Ref.get(startedRef), {
          while: (started) => !started,
        });

        controller.abort();

        const exit = yield* Fiber.join(fiber).pipe(Effect.exit);
        const interrupted = yield* Ref.get(interruptedRef);
        expect(interrupted).toBe(true);
        expect(exit._tag).toBe("Failure");

        if (exit._tag === "Failure") {
          const error = Cause.squash(exit.cause) as DOMException;
          expect(error).toBeInstanceOf(DOMException);
          expect(error.name).toBe("AbortError");
        }
      }),
  );
});
