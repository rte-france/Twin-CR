/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  HttpClient,
  HttpClientError,
} from "@effect/platform";
import { Effect, Layer, Schema, Duration } from "effect";
import { HttpClientRegistry } from "./registry";
import { ExtensionUriSchema } from "./schema";
import { makeHttpCache, type HttpCacheConfig } from "./cache";

// Format standard RFC 3986 : <extensionId>://<endpointName>/<path>
const EXTENSION_URI_REGEX = /^([a-zA-Z0-9_-]+):\/\/([a-zA-Z0-9_-]+)(?:\/.*)?$/;

export const makeHttpClientLayer = (config?: HttpCacheConfig) =>
  Layer.effect(
    HttpClient.HttpClient,
    Effect.gen(function* () {
      const registry = yield* HttpClientRegistry;
      const httpCache = yield* makeHttpCache(config);

      return HttpClient.make((request) =>
        Effect.gen(function* () {
          const uri = yield* Schema.decode(ExtensionUriSchema)(request.url).pipe(
            Effect.mapError(
              (e) =>
                new HttpClientError.RequestError({
                  request,
                  reason: "InvalidUrl",
                  cause: e,
                }),
            ),
          );

          const match = uri.match(EXTENSION_URI_REGEX);
          if (!match) {
            return yield* Effect.fail(
              new HttpClientError.RequestError({
                request,
                reason: "InvalidUrl",
                cause: new Error(
                  `URL must match 'extensionId://endpointName[/path]', got: ${uri}`,
                ),
              }),
            );
          }

          const extensionId = match[1];
          const extClient = yield* registry.getClient(extensionId);

          return yield* httpCache.execute(
            extensionId,
            request,
            extClient,
          );
        }),
      );
    }),
  );

export const HttpClientLayer = makeHttpClientLayer({
  capacity: 256,
  timeToLive: Duration.seconds(30),
});
