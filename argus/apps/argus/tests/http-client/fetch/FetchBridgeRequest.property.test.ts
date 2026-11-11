/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect, it } from "vitest";
import fc from "fast-check";
import { Effect, Layer } from "effect";
import { HttpClientResponse } from "@effect/platform";
import {
  HttpClientRegistry,
  FetchBridgeService,
  FetchBridgeLive,
} from "@/services/http-client";

type AbstractBody =
  | { _tag: "Empty" }
  | { _tag: "Text"; content: string; contentType: string }
  | { _tag: "Binary"; content: Uint8Array; contentType: string }
  | { _tag: "FormData"; fields: Record<string, string> };

interface HttpRequestModel {
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH" | "HEAD" | "OPTIONS";
  url: string;
  headers: Record<string, string>;
  body: AbstractBody;
}

const headersArb = fc.dictionary(
  fc
    .stringMatching(/^[a-z0-9-]+$/)
    .filter((k) => k !== "content-type" && k !== "content-length"),
  fc.stringMatching(/^[a-zA-Z0-9_ -]+$/),
  { maxKeys: 10 },
);

const bodyArb = fc.oneof(
  fc.record({ _tag: fc.constant("Empty" as const) }),
  fc.record({
    _tag: fc.constant("Text" as const),
    content: fc.string(),
    contentType: fc.constantFrom("text/plain", "application/json", "text/html"),
  }),
  fc.record({
    _tag: fc.constant("Binary" as const),
    content: fc.uint8Array({ maxLength: 2048 }),
    contentType: fc.constant("application/octet-stream"),
  }),
  fc.record({
    _tag: fc.constant("FormData" as const),
    fields: fc.dictionary(fc.string({ minLength: 1 }), fc.string(), {
      maxKeys: 10,
    }),
  }),
);

const httpRequestModelArb: fc.Arbitrary<HttpRequestModel> = fc
  .record({
    method: fc.constantFrom("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"),
    url: fc.webUrl().map((url) => `testClient:${url}`),
    headers: headersArb,
    body: bodyArb,
  })
  .map((model): HttpRequestModel => {
    if (model.method === "GET" || model.method === "HEAD") {
      return { ...model, body: { _tag: "Empty" } };
    }
    return model;
  });

describe("FetchBridge - fetch rebuilding", () => {
  it("strictly preserves the request contract (Method, URL, Headers, Body) across arbitrary inputs", async () => {
    await fc.assert(
      fc.asyncProperty(httpRequestModelArb, async (model) => {
        let capturedReq: any = null;

        const mockRegistry = Layer.succeed(HttpClientRegistry, {
          getClient: (_clientId: string) =>
            Effect.succeed({
              execute: (req: any) => {
                capturedReq = req;
                return Effect.succeed(
                  HttpClientResponse.fromWeb(
                    req,
                    new Response("ok", { status: 200 }),
                  ),
                );
              },
            } as any),
        } as any);

        const bridgeLayer = FetchBridgeLive.pipe(Layer.provide(mockRegistry));
        const bridge = await Effect.runPromise(
          FetchBridgeService.pipe(Effect.provide(bridgeLayer)),
        );

        const init: RequestInit = {
          method: model.method,
          headers: new Headers(model.headers),
        };

        if (model.body._tag === "Text") {
          init.body = model.body.content;
          (init.headers as Headers).set("Content-Type", model.body.contentType);
        } else if (model.body._tag === "Binary") {
          init.body = model.body.content as any;
          (init.headers as Headers).set("Content-Type", model.body.contentType);
        } else if (model.body._tag === "FormData") {
          const fd = new FormData();
          for (const [k, v] of Object.entries(model.body.fields)) {
            fd.append(k, v);
          }
          init.body = fd;
        }

        const response = await Effect.runPromise(
          bridge.execute(model.url, init),
        );

        expect(response.status).toBe(200);
        expect(capturedReq).not.toBeNull();
        expect(capturedReq.method).toBe(model.method);

        const expectedActualUrl = model.url.split("testClient:")[1];
        expect(capturedReq.url).toBe(expectedActualUrl);

        for (const [key, value] of Object.entries(model.headers)) {
          expect(capturedReq.headers[key.toLowerCase()]).toBe(value.trim());
        }

        if (model.body._tag === "Empty") {
          expect(["Empty", "Uint8Array"]).toContain(capturedReq.body._tag);
          if (capturedReq.body._tag === "Uint8Array") {
            expect(capturedReq.body.body.byteLength).toBe(0);
          }
        } else if (model.body._tag === "Text") {
          expect(capturedReq.body._tag).toBe("Uint8Array");
          const decoded = new TextDecoder().decode(capturedReq.body.body);
          expect(decoded).toBe(model.body.content);
          expect(capturedReq.headers["content-type"]).toBe(
            model.body.contentType,
          );
        } else if (model.body._tag === "Binary") {
          expect(capturedReq.body._tag).toBe("Uint8Array");
          expect(new Uint8Array(capturedReq.body.body)).toEqual(
            model.body.content,
          );
          expect(capturedReq.headers["content-type"]).toBe(
            model.body.contentType,
          );
        } else if (model.body._tag === "FormData") {
          expect(capturedReq.body._tag).toBe("FormData");
          for (const [k, v] of Object.entries(model.body.fields)) {
            expect(capturedReq.body.formData.get(k)).toBe(v);
          }
        }
      }),
      {
        numRuns: 100,
        verbose: true,
      },
    );
  });
});
