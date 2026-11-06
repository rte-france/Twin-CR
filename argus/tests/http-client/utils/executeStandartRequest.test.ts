/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect, Fiber } from "effect";
import { HttpClientRequest } from "@effect/platform";
import { mockIPC } from "@tauri-apps/api/mocks";

import { executeStandardRequest } from "@/services/http-client";
import { mockClient } from "../mocks/MockHttpClient";

describe("executeStandardRequest", () => {
  describe("Nominal Cases & Body Types", () => {
    it.effect("should handle Uint8Array body", () =>
      Effect.gen(function* () {
        mockClient.setRoute("POST", "https://api.test/binary", {
          status: 200,
          headers: {},
          body: "ok",
        });

        const req = HttpClientRequest.post("https://api.test/binary").pipe(
          HttpClientRequest.bodyUint8Array(new Uint8Array([1, 2, 3])),
        );
        const res = yield* executeStandardRequest("client-1", "req-1", req, {});
        expect(res.status).toBe(200);
      }),
    );

    it.effect("should convert and send FormData", () =>
      Effect.gen(function* () {
        mockClient.setRoute("POST", "https://api.test/form", {
          status: 200,
          headers: {},
          body: "ok",
        });

        const formData = new FormData();
        formData.append("key", "value");
        const req = HttpClientRequest.post("https://api.test/form").pipe(
          HttpClientRequest.bodyFormData(formData),
        );

        const res = yield* executeStandardRequest(
          "client-1",
          "req-form",
          req,
          {},
        );
        expect(res.status).toBe(200);
      }),
    );

    it.effect("should correctly route all HTTP methods", () =>
      Effect.gen(function* () {
        const methods = [
          "GET",
          "POST",
          "PUT",
          "PATCH",
          "DELETE",
          "HEAD",
          "OPTIONS",
          "TRACE",
        ] as const;

        for (const method of methods) {
          mockClient.setRoute(method, `https://api.test/${method}`, {
            status: 200,
            headers: {},
            body: "ok",
          });

          const req = HttpClientRequest.make(method as any)(
            `https://api.test/${method}`,
          );

          const res = yield* executeStandardRequest(
            "client-1",
            `req-${method}`,
            req,
            {},
          );

          expect(res.status).toBe(200);
        }
      }),
    );

    it.effect("should delegate to post_multipart_stream when FormData contains a File with local path", () =>
      Effect.gen(function* () {
        let invokedCommand: string | null = null;
        let receivedManifest: any = null;

        mockIPC((cmd, args: any) => {
          if (cmd === "post_multipart_stream") {
            invokedCommand = cmd;
            receivedManifest = args.manifest;
            return {
              status: 201,
              headers: { "content-type": "application/json" },
              body: JSON.stringify({ uploaded: true }),
            };
          }
        });

        const formData = new FormData();
        formData.append("desc", "test upload");

        const file = new File(["dummy content"], "sample.xml");
        Object.defineProperty(file, "path", {
          value: "/local/disk/sample.xml",
          writable: false,
        });
        formData.append("xml_file", file);

        const req = HttpClientRequest.post("https://api.test/upload").pipe(
          HttpClientRequest.bodyFormData(formData),
        );

        const res = yield* executeStandardRequest(
          "direct",
          "req-multipart-1",
          req,
          { authorization: "Bearer secret-token" },
        );

        expect(invokedCommand).toBe("post_multipart_stream");
        expect(receivedManifest).toBeDefined();
        expect(receivedManifest.clientId).toBe("direct");
        expect(receivedManifest.reqId).toBe("req-multipart-1");
        expect(receivedManifest.endpoint).toBe("https://api.test/upload");
        expect(receivedManifest.method).toBe("POST");
        expect(receivedManifest.fields).toEqual([{ name: "desc", value: "test upload" }]);
        expect(receivedManifest.files).toEqual([
          {
            fieldName: "xml_file",
            fileName: "sample.xml",
            localPath: "/local/disk/sample.xml",
          },
        ]);
        expect(res.status).toBe(201);
        const json = yield* res.json;
        expect(json).toEqual({ uploaded: true });
      }),
    );
  });

  describe("Fiber Management and Cancellation", () => {
    it.effect(
      "should invoke cancel_http_request if Effect is interrupted",
      () =>
        Effect.gen(function* () {
          let cancelCalled = false;
          let getStarted: () => void;
          const startedPromise = new Promise<void>((resolve) => {
            getStarted = resolve;
          });

          mockIPC((cmd) => {
            if (cmd === "cancel_http_request") {
              cancelCalled = true;
              return null;
            }
            if (cmd === "get") {
              getStarted();
              return new Promise(() => {});
            }
          });

          const req = HttpClientRequest.get("https://api.test/hang");

          const fiber = yield* Effect.fork(
            executeStandardRequest("client-1", "req-hang", req, {}),
          );

          yield* Effect.promise(() => startedPromise);
          yield* Fiber.interrupt(fiber);

          expect(cancelCalled).toBe(true);
        }),
    );

    it.effect(
      "should propagate TypeError when stream chunk errors",
      () =>
        Effect.gen(function* () {
          mockIPC((cmd, args: any) => {
            if (cmd === "get") {
              const onChunk = args.onChunk;
              setTimeout(() => {
                if (typeof onChunk.onmessage === "function") {
                  onChunk.onmessage({
                    type: "error",
                    message: "network connection reset",
                  });
                }
              }, 0);
              return {
                status: 200,
                headers: {},
              };
            }
          });

          const req = HttpClientRequest.get("https://api.test/stream-error");
          const res = yield* executeStandardRequest(
            "client-1",
            "req-stream-err",
            req,
            {},
          );

          const result = yield* Effect.either(res.text);
          expect(result._tag).toBe("Left");
          if (result._tag === "Left") {
            const cause = (result.left as any).cause;
            expect(cause).toBeInstanceOf(TypeError);
            expect(cause.message).toBe(
              "Failed to read response body: network connection reset",
            );
          }
        }),
    );
  });
});
