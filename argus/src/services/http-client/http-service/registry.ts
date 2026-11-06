/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { HttpClient, HttpClientRequest } from "@effect/platform";
import { Effect, Layer, Context, Ref, Option, HashMap } from "effect";

import type { ExtensionManifest } from "./types";
import type { TauriInvokeError } from "./errors";
import {
  executeSSERequest,
  executeStandardRequest,
  fetchManifestsFromRust,
} from "./utils";

export class HttpClientRegistry extends Context.Tag("HttpClientRegistry")<
  HttpClientRegistry,
  {
    readonly getAvailableExtensions: Effect.Effect<
      ExtensionManifest[],
      TauriInvokeError
    >;
    readonly getClient: (
      extensionId: string,
    ) => Effect.Effect<HttpClient.HttpClient, never>;
  }
>() {}

export const makeTauriHttpClient = (clientId: string) =>
  HttpClient.make((request) =>
    Effect.gen(function* () {
      const reqId = request.headers["x-argus-req-id"] ?? crypto.randomUUID();

      const headers: Record<string, string> = {
        ...request.headers,
      };
      delete headers["x-argus-req-id"];

      let finalUrl = request.url;

      if (Array.isArray(request.urlParams) && request.urlParams.length > 0) {
        const searchParams = new URLSearchParams();
        for (const [key, value] of request.urlParams) {
          searchParams.append(key, value);
        }
        finalUrl +=
          (finalUrl.includes("?") ? "&" : "?") + searchParams.toString();
      }

      const acceptHeader =
        request.headers["accept"] || request.headers["Accept"];
      const isSSE = acceptHeader === "text/event-stream";

      const finalRequest = HttpClientRequest.setUrl(finalUrl)(request);

      if (isSSE) {
        return yield* executeSSERequest(clientId, reqId, finalRequest, headers);
      }

      return yield* executeStandardRequest(
        clientId,
        reqId,
        finalRequest,
        headers,
      );
    }).pipe(
      Effect.annotateLogs({
        "extension.id": clientId,
        "http.method": request.method,
        "http.url": request.url,
      }),
      Effect.withSpan("HttpClient.Request"),
    ),
  );

export const HttpClientRegistryLive = Layer.effect(
  HttpClientRegistry,
  Effect.gen(function* () {
    const clientCache = yield* Ref.make(
      HashMap.empty<string, HttpClient.HttpClient>(),
    );

    yield* Effect.logDebug("Initialisation HttpClientRegistry");

    return {
      getAvailableExtensions: fetchManifestsFromRust,

      getClient: (extensionId: string) =>
        Effect.gen(function* () {
          const map = yield* Ref.get(clientCache);
          const existing = HashMap.get(map, extensionId);

          if (Option.isSome(existing)) return existing.value;

          const newClient = makeTauriHttpClient(extensionId);
          yield* Ref.update(clientCache, HashMap.set(extensionId, newClient));

          return newClient;
        }).pipe(
          Effect.annotateLogs("extension.id", extensionId),
          Effect.withSpan("HttpClientRegistry.GetClient", {
            attributes: { "extension.id": extensionId },
          }),
        ),
    };
  }),
).pipe(Layer.withSpan("HttpClientRegistryLive.Initialize"));
