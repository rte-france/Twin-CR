/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect, Layer, Ref } from "effect";
import { HttpClient, HttpClientResponse } from "@effect/platform";

import { HttpClientLayer } from "@/services/http-client";
import { HttpClientRegistry } from "@/services/http-client";

describe("HttpClientLayer", () => {
  it.effect("should pass the correct URL to the extension client", () =>
    Effect.gen(function* () {
      const urlRef = yield* Ref.make("");

      const mockExtClient = HttpClient.make((request) =>
        Effect.gen(function* () {
          yield* Ref.set(urlRef, request.url);
          return HttpClientResponse.fromWeb(request, new Response("ok"));
        }),
      );

      const MockRegistryLayer = Layer.succeed(HttpClientRegistry, {
        getAvailableExtensions: Effect.succeed([]),
        getClient: () => Effect.succeed(mockExtClient),
      });

      const client = yield* HttpClient.HttpClient.pipe(
        Effect.provide(HttpClientLayer),
        Effect.provide(MockRegistryLayer),
      );

      yield* client.get("extension://service/users/1");

      const finalUrl = yield* Ref.get(urlRef);
      expect(finalUrl).toBe("extension://service/users/1");
    }),
  );

  it.effect("should fail with InvalidUrl if the format is incorrect", () =>
    Effect.gen(function* () {
      const MockRegistryLayer = Layer.succeed(HttpClientRegistry, {
        getAvailableExtensions: Effect.succeed([]),
        getClient: () => Effect.die("Should not be called"),
      });

      const client = yield* HttpClient.HttpClient.pipe(
        Effect.provide(HttpClientLayer),
        Effect.provide(MockRegistryLayer),
      );

      const error = yield* Effect.flip(client.get("invalid_url_no_colon"));

      expect(error._tag).toBe("RequestError");
      expect(error.reason).toBe("InvalidUrl");
    }),
  );
});
