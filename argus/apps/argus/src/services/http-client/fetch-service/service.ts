/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  Effect,
  Context,
  Layer,
  Scope,
  Stream,
  Exit,
  Schema,
  ParseResult,
} from "effect";
import { HttpClientRequest, HttpClientResponse } from "@effect/platform";

import { HttpClientRegistry } from "../http-service/registry";
import { DIRECT_CLIENT_ID, parseBridgeUrl } from "./interceptor";

export class FetchBridgeService extends Context.Tag("FetchBridgeService")<
  FetchBridgeService,
  {
    execute: (
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => Effect.Effect<Response, Error, never>;
  }
>() {}

const NULL_BODY_STATUSES = [204, 205, 304];

/**
 * Hop-by-hop and framing headers that must not be forwarded
 * to prevent proxy-level protocol desync and decompression mismatches.
 */
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "content-length",
]);

const MethodSchema = Schema.transformOrFail(
  Schema.String,
  Schema.Literal("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"),
  {
    decode: (s, _, ast) => {
      const upper = s.toUpperCase();
      const validMethods = [
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "HEAD",
        "OPTIONS",
      ];
      return validMethods.includes(upper)
        ? Effect.succeed(upper as any)
        : Effect.fail(new ParseResult.Type(ast, s));
    },
    encode: (s) => Effect.succeed(s),
  },
);

const HeadersSchema = Schema.transform(
  Schema.Unknown,
  Schema.Record({ key: Schema.String, value: Schema.String }),
  {
    strict: false,
    decode: (unknownHeaders) => {
      if (!unknownHeaders) return {};
      const h = new Headers(unknownHeaders as HeadersInit);
      const record: Record<string, string> = {};
      h.forEach((v, k) => {
        record[k] = v;
      });
      return record;
    },
    encode: (record) => record,
  },
);

const BridgeUrlSchema = Schema.transformOrFail(
  Schema.String,
  Schema.Struct({
    clientId: Schema.NonEmptyString,
    actualUrl: Schema.NonEmptyString,
  }),
  {
    decode: (rawUrl, _, ast) => {
      const parsed = parseBridgeUrl(rawUrl);
      return parsed
        ? Effect.succeed(parsed)
        : Effect.fail(new ParseResult.Type(ast, rawUrl, "INVALID_URL_FORMAT"));
    },
    encode: (obj) =>
      Effect.succeed(
        obj.clientId === DIRECT_CLIENT_ID
          ? obj.actualUrl
          : `${obj.clientId}:${obj.actualUrl}`,
      ),
  },
);

const NormalizedRequestSchema = Schema.Struct({
  url: BridgeUrlSchema,
  method: Schema.optionalWith(MethodSchema, { default: () => "GET" }),
  headers: Schema.optionalWith(HeadersSchema, { default: () => ({}) }),
});

const getAbortError = (signal?: AbortSignal | null) =>
  signal?.reason ?? new DOMException("The operation was aborted", "AbortError");

const sanitizeResponseHeaders = (
  rawHeaders: Record<string, string>,
): Record<string, string> => {
  const sanitized: Record<string, string> = {};
  for (const [key, value] of Object.entries(rawHeaders)) {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      sanitized[key] = value;
    }
  }
  return sanitized;
};

const resolveBody = (input: RequestInfo | URL, init?: RequestInit) =>
  Effect.gen(function* () {
    if (init?.body !== undefined) return init.body;
    if (
      typeof input === "object" &&
      input !== null &&
      "body" in input &&
      (input as Request).body
    ) {
      // Use arrayBuffer() to preserve binary payload integrity
      return yield* Effect.promise(() =>
        (input as Request).clone().arrayBuffer(),
      );
    }
    return undefined;
  });

const isFormData = (b: unknown): b is FormData =>
  typeof FormData !== "undefined" && b instanceof FormData;

const isURLSearchParams = (b: unknown): b is URLSearchParams =>
  typeof URLSearchParams !== "undefined" && b instanceof URLSearchParams;

const isReadableStream = (b: unknown): b is ReadableStream<Uint8Array> =>
  typeof ReadableStream !== "undefined" && b instanceof ReadableStream;

const hasArrayBufferMethod = (
  b: unknown,
): b is { arrayBuffer: () => Promise<ArrayBuffer> } =>
  typeof b === "object" &&
  b !== null &&
  typeof (b as any).arrayBuffer === "function";

const applyRequestBody = (
  req: HttpClientRequest.HttpClientRequest,
  body: BodyInit | undefined | null,
) => {
  if (body === undefined || body === null) return Effect.succeed(req);

  const contentType =
    req.headers["content-type"] ?? req.headers["Content-Type"];

  if (typeof body === "string") {
    return Effect.succeed(
      req.pipe(HttpClientRequest.bodyText(body, contentType)),
    );
  }
  if (isURLSearchParams(body)) {
    return Effect.succeed(
      req.pipe(HttpClientRequest.bodyText(body.toString(), contentType)),
    );
  }

  if (isFormData(body)) {
    return Effect.succeed(req.pipe(HttpClientRequest.bodyFormData(body)));
  }

  // Stream directly to prevent high memory usage during large uploads
  if (isReadableStream(body)) {
    return Effect.succeed(
      req.pipe(
        HttpClientRequest.bodyStream(
          Stream.fromReadableStream(
            () => body,
            (error) => new Error(`Stream read failure: ${String(error)}`),
          ),
          contentType ? { contentType} : undefined,
        ),
      ),
    );
  }

  if (body instanceof ArrayBuffer) {
    const uint8 = new Uint8Array(body);
    return Effect.succeed(
      req.pipe(HttpClientRequest.bodyUint8Array(uint8 as any, contentType)),
    );
  }
  if (ArrayBuffer.isView(body)) {
    const uint8 = new Uint8Array(
      body.buffer as ArrayBuffer,
      body.byteOffset,
      body.byteLength,
    );
    return Effect.succeed(
      req.pipe(HttpClientRequest.bodyUint8Array(uint8 as any, contentType)),
    );
  }

  // Fallback for Blob and unknown BodyInit types
  return Effect.promise(async () => {
    if (hasArrayBufferMethod(body)) {
      return await body.arrayBuffer();
    }
    return await new Response(body as any).arrayBuffer();
  }).pipe(
    Effect.map((buffer) => {
      const uint8 = new Uint8Array(buffer);
      return req.pipe(
        HttpClientRequest.bodyUint8Array(uint8 as any, contentType),
      );
    }),
  );
};

const executeWithSignal = <E, R>(
  executeRequest: Effect.Effect<HttpClientResponse.HttpClientResponse, E, R>,
  signal?: AbortSignal | null,
) => {
  if (!signal) return executeRequest;

  return Effect.raceFirst(
    executeRequest,
    Effect.async<never, unknown, never>((resume) => {
      const onAbort = () => resume(Effect.fail(getAbortError(signal)));
      signal.addEventListener("abort", onAbort, { once: true });
      return Effect.sync(() => signal.removeEventListener("abort", onAbort));
    }),
  );
};

const createWebResponse = (
  response: HttpClientResponse.HttpClientResponse,
  scope: Scope.CloseableScope,
): Effect.Effect<Response> => {
  const headers = sanitizeResponseHeaders(
    response.headers as Record<string, string>,
  );

  // Fast-path: Close scope immediately for null-body statuses to adhere to Web API spec
  if (NULL_BODY_STATUSES.includes(response.status)) {
    return Scope.close(scope, Exit.void).pipe(
      Effect.as(
        new Response(null, {
          status: response.status,
          headers,
        }),
      ),
    );
  }

  // Stream-path: Defer scope closure until the web consumer drains or aborts the stream
  return Effect.sync(() => {
    const streamWithScope = response.stream.pipe(
      Stream.ensuring(Scope.close(scope, Exit.void)),
    );

    return new Response(Stream.toReadableStream(streamWithScope), {
      status: response.status,
      headers,
    });
  });
};

const handleBridgeError = (error: unknown) => {
  if (
    error instanceof DOMException ||
    (error instanceof Error && error.name === "AbortError")
  ) {
    return Effect.fail(error as Error);
  }

  const isInvalidUrl =
    typeof error === "object" &&
    error !== null &&
    "_tag" in error &&
    error._tag === "ParseError";

  const realError =
    typeof error === "object" &&
    error !== null &&
    "_tag" in error &&
    error._tag === "RequestError"
      ? (error as any).cause
      : error;

  const message = isInvalidUrl ? "Invalid URL format" : String(realError);

  return Effect.logWarning(`[HTTP BRIDGE] Network failure: ${message}`).pipe(
    Effect.zipRight(Effect.fail(new TypeError(`Failed to fetch: ${message}`))),
  );
};

export const FetchBridgeLive = Layer.effect(
  FetchBridgeService,
  Effect.gen(function* () {
    const registry = yield* HttpClientRegistry;

    return {
      execute: (input: RequestInfo | URL, init?: RequestInit) =>
        Effect.gen(function* () {
          const isInputRequest =
            typeof input === "object" &&
            input !== null &&
            "url" in input &&
            typeof (input as any).url === "string";

          const signal =
            init?.signal ||
            (isInputRequest ? (input as Request).signal : undefined);

          // Fast-path abort verification
          if (signal?.aborted) {
            return yield* Effect.fail(getAbortError(signal));
          }

          // Normalize input to handle String, URL instances, or Request objects
          const rawPayload: any = {
            url: isInputRequest ? (input as Request).url : String(input),
          };
          if (init?.method || (isInputRequest && (input as Request).method)) {
            rawPayload.method = init?.method || (input as Request).method;
          }
          if (init?.headers || (isInputRequest && (input as Request).headers)) {
            rawPayload.headers = init?.headers || (input as Request).headers;
          }

          const { url, method, headers } = yield* Schema.decodeUnknown(
            NormalizedRequestSchema,
          )(rawPayload);

          yield* Effect.annotateCurrentSpan("http.url", url.actualUrl);
          yield* Effect.annotateCurrentSpan("http.method", method);
          yield* Effect.annotateCurrentSpan("argus.client_id", url.clientId);

          const baseReq = HttpClientRequest.make(method)(url.actualUrl).pipe(
            HttpClientRequest.setHeaders(headers),
          );

          const rawBody = yield* resolveBody(input, init);
          const req = yield* applyRequestBody(baseReq, rawBody);

          const client = yield* registry.getClient(url.clientId);
          const scope = yield* Scope.make();

          const executeRequestEffect = client
            .execute(req)
            .pipe(Scope.extend(scope));

          // Ensure scope is reclaimed if the request fails or is aborted before stream handoff
          const response = yield* executeWithSignal(
            executeRequestEffect,
            signal,
          ).pipe(
            Effect.onExit((exit) =>
              Exit.isSuccess(exit)
                ? Effect.void
                : Scope.close(scope, Exit.void),
            ),
          );

          yield* Effect.annotateCurrentSpan("http.status", response.status);

          // Convert to Web Response; guarantee scope cleanup if Response instantiation fails
          return yield* createWebResponse(response, scope).pipe(
            Effect.onError(() => Scope.close(scope, Exit.void)),
          );
        }).pipe(
          Effect.catchAll(handleBridgeError),
          Effect.withSpan("FetchBridge.Execute", { kind: "client" }),
        ),
    };
  }),
);
