/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Chunk, Effect, Stream } from "effect";
import {
  HttpClientError,
  HttpClientRequest,
  HttpClientResponse,
} from "@effect/platform";
import { dual } from "effect/Function";
import { Channel, invoke } from "@tauri-apps/api/core";
import type { ExtensionManifest } from "./types";
import { TauriInvokeError } from "./errors";
import type { ExtensionUri } from "./schema";

export interface FilePartDescriptor {
  readonly fieldName: string;
  readonly fileName: string;
  readonly localPath: string;
}

export interface MultipartFieldDescriptor {
  readonly name: string;
  readonly value: string;
}

export interface MultipartManifest {
  readonly clientId: string;
  readonly reqId: string;
  readonly endpoint: string;
  readonly method: string;
  readonly headers: Record<string, string>;
  readonly fields: MultipartFieldDescriptor[];
  readonly files: FilePartDescriptor[];
}

export const makeEndpointUri: {
  (path: string, endpointAlias: string): ExtensionUri;
  (endpointAlias: string): (path: string) => ExtensionUri;
} = dual(2, (path: string, endpointAlias: string): ExtensionUri => {
  const cleanPath = path.replace(/^\/+/, "");
  return `${endpointAlias}://${cleanPath}` as ExtensionUri;
});

const concatUint8Arrays = (chunks: ReadonlyArray<Uint8Array>): Uint8Array => {
  const totalLength = chunks.reduce((acc, curr) => acc + curr.byteLength, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return result;
};

export const executeSSERequest = (
  clientId: string,
  reqId: string,
  request: HttpClientRequest.HttpClientRequest,
  headers: Record<string, string>,
) =>
  Effect.sync(() => {
    const channel = new Channel<string>();
    let isStreamAborted = false;
    const encoder = new TextEncoder();

    const stream = new ReadableStream({
      start(controller) {
        channel.onmessage = (event) => {
          if (isStreamAborted) return;

          if (event === "[CLOSE]") {
            controller.close();
          } else if (event.startsWith("ERROR: ")) {
            controller.error(new Error(event));
          } else {
            // Receive a W3C standart SSE (data:, id:, \n\n)
            controller.enqueue(encoder.encode(event));
          }
        };

        invoke("sse", {
          clientId,
          reqId,
          endpoint: request.url,
          headers,
          onEvent: channel,
        }).catch((error) => {
          if (!isStreamAborted) controller.error(error);
        });
      },
      cancel() {
        isStreamAborted = true;
        invoke("cancel_http_request", { clientId, reqId }).catch(() => {});
      },
    });

    return HttpClientResponse.fromWeb(
      request,
      new Response(stream, {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      }),
    );
  }).pipe(
    Effect.onInterrupt(() =>
      Effect.promise(() => {
        return invoke("cancel_http_request", { clientId, reqId });
      }).pipe(Effect.ignore),
    ),
    Effect.withSpan("TauriHttpClient.ExecuteSSE", {
      attributes: {
        "http.url": request.url,
        "extension.id": clientId,
        "req.id": reqId,
      },
    }),
  );

export const executeStandardRequest = (
  clientId: string,
  reqId: string,
  request: HttpClientRequest.HttpClientRequest,
  headers: Record<string, string>,
) =>
  Effect.gen(function* () {
    const method = request.method.toLowerCase();

    let bodyPayload: Uint8Array;
    const reqHeaders = { ...headers };

    if ("contentType" in request.body && request.body.contentType) {
      reqHeaders["content-type"] = request.body.contentType.toString();
    }

    if (request.body._tag === "FormData") {
      const formData = request.body.formData;
      const fields: MultipartFieldDescriptor[] = [];
      const files: FilePartDescriptor[] = [];
      let hasFileWithoutPath = false;

      // O(1) memory traversal using standard File.path property
      formData.forEach((value, key) => {
        if (value instanceof File) {
          const path =
            "path" in value && typeof (value as any).path === "string"
              ? (value as any).path
              : undefined;
          if (path) {
            files.push({
              fieldName: key,
              fileName: value.name,
              localPath: path,
            });
          } else {
            hasFileWithoutPath = true;
          }
        } else if (typeof value === "string") {
          fields.push({ name: key, value });
        }
      });

      if (files.length > 0 && hasFileWithoutPath) {
        return yield* Effect.fail(
          new HttpClientError.RequestError({
            request,
            reason: "Transport",
            cause: new Error(
              "Cannot mix disk-backed files and in-memory files in FormData",
            ),
          }),
        );
      }

      // If the form contains files on disk, we delegate to Rust streaming
      if (files.length > 0) {
        // Removes the JS Content-Type to let reqwest generate the correct multipart boundary
        delete reqHeaders["content-type"];
        delete reqHeaders["Content-Type"];

        const manifest: MultipartManifest = {
          clientId,
          reqId,
          endpoint: request.url,
          method: request.method.toUpperCase(),
          headers: reqHeaders,
          fields,
          files,
        };

        const res = yield* Effect.tryPromise({
          try: () =>
            invoke<{
              status: number;
              headers: Record<string, string>;
              body: string;
            }>("post_multipart_stream", { manifest }),
          catch: (cause) =>
            new HttpClientError.RequestError({
              request,
              reason: "Transport",
              cause,
            }),
        }).pipe(
          Effect.onInterrupt(() =>
            Effect.promise(() =>
              invoke("cancel_http_request", { clientId, reqId }),
            ).pipe(Effect.ignore),
          ),
        );

        const statusesWithNoBody = [204, 205, 304];
        const finalBody = statusesWithNoBody.includes(res.status)
          ? null
          : res.body;

        return HttpClientResponse.fromWeb(
          request,
          new Response(finalBody, {
            status: res.status,
            headers: res.headers,
          }),
        );
      }
    }

    if (request.body._tag === "Uint8Array") {
      bodyPayload = new Uint8Array(request.body.body);
    } else if (request.body._tag === "FormData") {
      // Hack: using Request to convert FormData to Uint8Array (faster way to serialize with browser)
      // This url is fake and does not need to be valid
      const nativeReq = new Request("http://internal-multipart-builder.test", {
        method: "POST",
        body: request.body.formData,
      });

      const contentType = nativeReq.headers.get("content-type");
      if (contentType) {
        reqHeaders["content-type"] = contentType;
      }

      const buffer = yield* Effect.promise(() => nativeReq.arrayBuffer());
      bodyPayload = new Uint8Array(buffer);
    } else if (request.body._tag === "Stream") {
      const chunks = yield* Stream.runCollect(request.body.stream).pipe(
        Effect.mapError(
          (cause) =>
            new HttpClientError.RequestError({
              request,
              reason: "Transport",
              cause,
            }),
        ),
      );
      bodyPayload = concatUint8Arrays(Chunk.toReadonlyArray(chunks));
    } else {
      bodyPayload = new Uint8Array();
    }

    const channel = new Channel<
      | ArrayBuffer
      | Uint8Array
      | { type: "end" }
      | { type: "error"; message: string }
    >();
    let isStreamAborted = false;

    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        channel.onmessage = (msg: any) => {
          if (isStreamAborted) return;
          if (msg instanceof ArrayBuffer) {
            controller.enqueue(new Uint8Array(msg));
          } else if (ArrayBuffer.isView(msg)) {
            controller.enqueue(
              new Uint8Array(msg.buffer, msg.byteOffset, msg.byteLength),
            );
          } else if (msg.type === "end") {
            controller.close();
          } else {
            controller.error(
              new TypeError(`Failed to read response body: ${msg.message}`),
            );
          }
        };
      },
      cancel() {
        isStreamAborted = true;
        invoke("cancel_http_request", { clientId, reqId }).catch(() => {});
      },
    });

    const { status, headers: responseHeaders } = yield* Effect.tryPromise({
      try: () =>
        invoke<{ status: number; headers: Record<string, string> }>(method, {
          clientId,
          reqId,
          endpoint: request.url,
          headers: reqHeaders,
          body: bodyPayload,
          onChunk: channel,
        }),
      catch: (cause) =>
        new HttpClientError.RequestError({
          request,
          reason: "Transport",
          cause,
        }),
    }).pipe(
      Effect.onInterrupt(() =>
        Effect.promise(() =>
          invoke("cancel_http_request", { clientId, reqId }),
        ).pipe(Effect.ignore),
      ),
    );

    const statusesWithNoBody = [204, 205, 304];
    const finalBody = statusesWithNoBody.includes(status) ? null : stream;

    return HttpClientResponse.fromWeb(
      request,
      new Response(finalBody, {
        status,
        headers: responseHeaders,
      }),
    );
  }).pipe(
    Effect.withSpan("TauriHttpClient.ExecuteStandard", {
      attributes: {
        "http.url": request.url,
        "http.method": request.method,
        "extension.id": clientId,
      },
    }),
  );

/**
 * TODO: Hook up with the Rust Tauri backend ("get_available_extensions")
 * once the extension feature is fully integrated.
 *
 * Blocked on extension system feature implementation.
 * Original implementation:
 * Effect.tryPromise({
 *   try: () => invoke<ExtensionManifest[]>("get_available_extensions"),
 *   catch: (cause) =>
 *     new TauriInvokeError({ method: "get_available_extensions", cause }),
 * })
 */
export const fetchManifestsFromRust: Effect.Effect<
  ExtensionManifest[],
  TauriInvokeError
> = Effect.succeed<ExtensionManifest[]>([]).pipe(
  Effect.withSpan("Tauri.GetAvailableExtensions"),
);
