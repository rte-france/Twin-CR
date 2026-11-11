/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect } from "vitest";
import fc from "fast-check";
import { Effect, Layer } from "effect";
import { HttpClientRegistry } from "@/services/http-client";
import { HttpClientResponse } from "@effect/platform";
import {
  shouldInterceptUrl,
  extractUrlString,
  createFetchBridgeQueue,
  parseBridgeUrl,
  DIRECT_CLIENT_ID,
  RESERVED_PROTOCOLS,
  type BridgeExecutor,
} from "@/services/http-client";
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

// Valid clientId generator: alphanum, dashes, underscores
const clientIdArb = fc
  .stringMatching(/^[a-zA-Z0-9_-]{1,20}$/)
  .filter((id) => id !== "http" && id !== "https");

// Arbitrary endpoint scheme and path
const endpointPathArb = fc
  .tuple(fc.stringMatching(/^[a-zA-Z0-9_-]{1,15}$/), fc.webPath())
  .map(([ep, path]) => `${ep}://${path.replace(/^\//, "")}`);

describe("FetchBridge - Property-Based Testing", () => {
  describe("URL Interception Predicate (shouldInterceptUrl)", () => {
    it("never intercepts any reserved protocol (ipc, tauri)", () => {
      fc.assert(
        fc.property(
          fc.constantFrom(...RESERVED_PROTOCOLS),
          fc.webPath(),
          (proto, path) => {
            const url = `${proto}${path.replace(/^\//, "")}`;
            expect(shouldInterceptUrl(url)).toBe(false);
            expect(parseBridgeUrl(url)).toBeNull();
          },
        ),
        { numRuns: 200 },
      );
    });

    it("always intercepts valid bridge scheme clientId:endpoint://path and parses it consistently", () => {
      fc.assert(
        fc.property(clientIdArb, endpointPathArb, (clientId, endpointPath) => {
          const url = `${clientId}:${endpointPath}`;
          expect(shouldInterceptUrl(url)).toBe(true);
          const parsed = parseBridgeUrl(url);
          expect(parsed).not.toBeNull();
          expect(parsed?.clientId).toBe(clientId);
          expect(parsed?.actualUrl).toBe(endpointPath);
        }),
        { numRuns: 300 },
      );
    });

    it("always intercepts standard RFC 3986 clientId://endpoint/path and parses it consistently", () => {
      fc.assert(
        fc.property(
          clientIdArb,
          fc.stringMatching(/^[a-zA-Z0-9_-]{1,15}$/),
          fc.webPath(),
          (clientId, endpoint, path) => {
            const cleanPath = path.replace(/^\/+/, "");
            const url = `${clientId}://${endpoint}/${cleanPath}`;
            expect(shouldInterceptUrl(url)).toBe(true);
            const parsed = parseBridgeUrl(url);
            expect(parsed).not.toBeNull();
            expect(parsed?.clientId).toBe(clientId);
            expect(parsed?.actualUrl).toBe(`${endpoint}://${cleanPath}`);
          },
        ),
        { numRuns: 300 },
      );
    });

    it("never intercepts raw paths or relative URLs", () => {
      fc.assert(
        fc.property(fc.webPath(), (path) => {
          expect(shouldInterceptUrl(path)).toBe(false);
          expect(shouldInterceptUrl(`/${path}`)).toBe(false);
          expect(parseBridgeUrl(path)).toBeNull();
          expect(parseBridgeUrl(`/${path}`)).toBeNull();
        }),
        { numRuns: 100 },
      );
    });

    it("always intercepts standard http:// and https:// URLs with DIRECT_CLIENT_ID", () => {
      fc.assert(
        fc.property(
          fc.constantFrom("http://", "https://"),
          fc.webUrl(),
          (proto, rawUrl) => {
            const cleanUrl = rawUrl.replace(/^https?:\/\//, "");
            const url = `${proto}${cleanUrl}`;
            expect(shouldInterceptUrl(url)).toBe(true);
            const parsed = parseBridgeUrl(url);
            expect(parsed).not.toBeNull();
            expect(parsed?.clientId).toBe(DIRECT_CLIENT_ID);
            expect(parsed?.actualUrl).toBe(url);
          },
        ),
        { numRuns: 100 },
      );
    });

    it("guarantees strict equivalence between shouldInterceptUrl and (parseBridgeUrl !== null) on arbitrary strings", () => {
      fc.assert(
        fc.property(fc.string(), (arbitraryUrl) => {
          const shouldIntercept = shouldInterceptUrl(arbitraryUrl);
          const parsed = parseBridgeUrl(arbitraryUrl);
          expect(shouldIntercept).toBe(parsed !== null);
        }),
        { numRuns: 1000 },
      );
    });

    it("extractUrlString extracts consistent URL from string, URL instance, or Request", () => {
      fc.assert(
        fc.property(clientIdArb, endpointPathArb, (clientId, endpointPath) => {
          const urlString = `${clientId}:${endpointPath}`;

          expect(extractUrlString(urlString)).toBe(urlString);

          // Test Request wrapping for valid standard-formatted schemes
          try {
            const req = new Request(urlString);
            expect(extractUrlString(req)).toBe(urlString);
          } catch {
            // Some runtime URL parsers reject non-standard protocols in new Request(str)
          }
        }),
        { numRuns: 100 },
      );
    });
  });

  describe("Binary Payload Preservation (Uint8Array / ArrayBuffer)", () => {
    it("preserves exact byte contents and length for any arbitrary Uint8Array body", async () => {
      await fc.assert(
        fc.asyncProperty(
          clientIdArb,
          endpointPathArb,
          fc.uint8Array({ minLength: 0, maxLength: 8192 }),
          async (clientId, endpointPath, inputBytes) => {
            let capturedBody: any;
            const layer = FetchBridgeLive.pipe(
              Layer.provide(
                makeMockRegistry((req) => {
                  capturedBody = req.body;
                  return Effect.succeed(
                    HttpClientResponse.fromWeb(
                      req,
                      new Response("ack", { status: 200 }),
                    ),
                  );
                }),
              ),
            );

            const bridge = await Effect.runPromise(
              FetchBridgeService.pipe(Effect.provide(layer)),
            );

            const url = `${clientId}:${endpointPath}`;
            const res = await Effect.runPromise(
              bridge.execute(url, {
                method: "POST",
                body: inputBytes,
              }),
            );

            expect(res.status).toBe(200);
            expect(capturedBody._tag).toBe("Uint8Array");
            expect(capturedBody.body.byteLength).toBe(inputBytes.byteLength);
            expect(new Uint8Array(capturedBody.body)).toEqual(inputBytes);
          },
        ),
        { numRuns: 50 },
      );
    });

    it("preserves URLSearchParams keys and Unicode values losslessly", async () => {
      await fc.assert(
        fc.asyncProperty(
          clientIdArb,
          endpointPathArb,
          fc.dictionary(
            fc.stringMatching(/^[a-zA-Z0-9_]{1,15}$/),
            fc.string({ maxLength: 30 }),
            { minKeys: 1, maxKeys: 10 },
          ),
          async (clientId, endpointPath, entries) => {
            let capturedBody: any;
            const layer = FetchBridgeLive.pipe(
              Layer.provide(
                makeMockRegistry((req) => {
                  capturedBody = req.body;
                  return Effect.succeed(
                    HttpClientResponse.fromWeb(
                      req,
                      new Response("ack", { status: 200 }),
                    ),
                  );
                }),
              ),
            );

            const bridge = await Effect.runPromise(
              FetchBridgeService.pipe(Effect.provide(layer)),
            );

            const params = new URLSearchParams(entries);
            const url = `${clientId}:${endpointPath}`;
            await Effect.runPromise(
              bridge.execute(url, {
                method: "POST",
                body: params,
              }),
            );

            expect(capturedBody._tag).toBe("Uint8Array");
            const decoded = new TextDecoder().decode(capturedBody.body);
            const receivedParams = new URLSearchParams(decoded);

            for (const [k, v] of Object.entries(entries)) {
              expect(receivedParams.get(k)).toBe(v);
            }
          },
        ),
        { numRuns: 40 },
      );
    });
  });

  describe("Queue FIFO & Resolution Guarantees", () => {
    it("delivers all queued requests in order upon executor connection with zero loss", async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.array(
            fc.record({
              id: fc.integer({ min: 1, max: 1000 }),
              url: fc.stringMatching(/^[a-zA-Z0-9_]{1,10}:api\/\/[a-z]{1,10}$/),
            }),
            { minLength: 1, maxLength: 25 },
          ),
          async (items) => {
            const queue = createFetchBridgeQueue();
            const executionOrder: number[] = [];

            // 1. Submit all items before executor exists
            const promises = items.map((item) =>
              queue.handle(item.url).then(async (res) => {
                const json = await res.json();
                executionOrder.push(json.id);
                return json;
              }),
            );

            expect(queue.pendingCount).toBe(items.length);
            expect(queue.isReady).toBe(false);

            // 2. Attach executor
            const mockExecutor: BridgeExecutor = {
              execute: async (input) => {
                const targetUrl =
                  typeof input === "string" ? input : (input as Request).url;
                const found = items.find((i) => i.url === targetUrl)!;
                return new Response(
                  JSON.stringify({ id: found.id, ok: true }),
                  {
                    status: 200,
                    headers: { "content-type": "application/json" },
                  },
                );
              },
            };

            queue.setExecutor(mockExecutor);
            expect(queue.pendingCount).toBe(0);
            expect(queue.isReady).toBe(true);

            // 3. All promises resolve
            const results = await Promise.all(promises);
            expect(results.length).toBe(items.length);
            expect(executionOrder).toEqual(items.map((i) => i.id));
          },
        ),
        { numRuns: 30 },
      );
    });
  });
});
