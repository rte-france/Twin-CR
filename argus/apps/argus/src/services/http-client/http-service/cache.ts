/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Effect, Cache, Duration, Equal, Hash } from "effect";
import {
  HttpClient,
  HttpClientRequest,
  HttpClientResponse,
} from "@effect/platform";

export interface CachedResponse {
  readonly status: number;
  readonly headers: Readonly<Record<string, string>>;
  readonly body: Uint8Array | null;
}

export interface HttpCacheConfig {
  readonly capacity?: number;
  readonly timeToLive?: Duration.DurationInput;
  readonly varyHeaders?: ReadonlyArray<string>;
}

const DEFAULT_VARY_HEADERS: ReadonlyArray<string> = [
  "authorization",
  "accept",
  "accept-language",
];

const getHeader = (
  headers: Readonly<Record<string, string>>,
  name: string,
): string | undefined => {
  const target = name.toLowerCase();
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() === target) {
      return headers[key];
    }
  }
  return undefined;
};

const isSafeMethod = (method: string): boolean =>
  method === "GET" || method === "HEAD";

const isCacheableRequest = (request: HttpClientRequest.HttpClientRequest): boolean => {
  if (!isSafeMethod(request.method)) return false;
  const cacheControl = getHeader(request.headers, "cache-control");
  if (
    cacheControl &&
    (cacheControl.includes("no-cache") || cacheControl.includes("no-store"))
  ) {
    return false;
  }
  return true;
};

const buildCacheKey = (
  extensionId: string,
  request: HttpClientRequest.HttpClientRequest,
  varyHeaders: ReadonlyArray<string>,
): string => {
  const varySegments = varyHeaders
    .map((header) => {
      const val = getHeader(request.headers, header);
      return val ? `${header.toLowerCase()}=${val}` : null;
    })
    .filter((segment): segment is string => segment !== null)
    .join(";");

  return `${extensionId}:${request.method}:${request.url}#${varySegments}`;
};

/**
 * Internal error indicating that a response should bypass caching
 * (e.g. non-2xx status codes or upstream no-store directives).
 * Effect Cache does not persist failures, avoiding cache poisoning.
 */
class NonCacheableResponse {
  readonly _tag = "NonCacheableResponse";
  constructor(readonly response: CachedResponse) {}
}

/**
 * Composite cache key delivering request context and client to lookup
 * without external mutable state. Equality and hashing are based solely on `id`.
 */
class HttpLookupKey implements Equal.Equal {
  constructor(
    readonly id: string,
    readonly request: HttpClientRequest.HttpClientRequest,
    readonly client: HttpClient.HttpClient,
  ) {}

  [Equal.symbol](that: unknown): boolean {
    return that instanceof HttpLookupKey && this.id === that.id;
  }

  [Hash.symbol](): number {
    return Hash.string(this.id);
  }
}

export const makeHttpCache = (config?: HttpCacheConfig) =>
  Effect.gen(function* () {
    const varyHeaders = config?.varyHeaders ?? DEFAULT_VARY_HEADERS;

    const cache = yield* Cache.make({
      capacity: config?.capacity ?? 256,
      timeToLive: config?.timeToLive ?? Duration.seconds(30),
      lookup: (key: HttpLookupKey) =>
        Effect.gen(function* () {
          const response = yield* key.client.execute(key.request);
          const bodyBytes = yield* response.arrayBuffer;
          const body =
            bodyBytes.byteLength > 0 ? new Uint8Array(bodyBytes) : null;

          const resCacheControl = getHeader(response.headers, "cache-control");
          const hasNoStore =
            resCacheControl &&
            (resCacheControl.includes("no-store") ||
              resCacheControl.includes("no-cache"));

          const candidate: CachedResponse = {
            status: response.status,
            headers: response.headers,
            body,
          };

          if (response.status < 200 || response.status >= 300 || hasNoStore) {
            return yield* Effect.fail(new NonCacheableResponse(candidate));
          }

          return candidate;
        }),
    });

    return {
      execute: (
        extensionId: string,
        request: HttpClientRequest.HttpClientRequest,
        client: HttpClient.HttpClient,
      ) => {
        if (!isCacheableRequest(request)) {
          const isMutation = !isSafeMethod(request.method);
          const executeReq = client.execute(request);

          if (isMutation) {
            return executeReq.pipe(
              Effect.tap(() =>
                Effect.gen(function* () {
                  const size = yield* cache.size;
                  if (size > 0) {
                    yield* cache.invalidateAll;
                  }
                }),
              ),
            );
          }

          return executeReq;
        }

        const cacheKeyId = buildCacheKey(extensionId, request, varyHeaders);
        const lookupKey = new HttpLookupKey(cacheKeyId, request, client);

        return Effect.gen(function* () {
          const cached = yield* cache.get(lookupKey).pipe(
            Effect.tapError(() => cache.invalidate(lookupKey)),
            Effect.catchTag("NonCacheableResponse", (err) =>
              Effect.succeed(err.response),
            ),
          );

          return HttpClientResponse.fromWeb(
            request,
            new Response(cached.body ? cached.body.slice() : null, {
              status: cached.status,
              headers: cached.headers,
            }),
          );
        });
      },
      invalidateAll: cache.invalidateAll,
    };
  });
