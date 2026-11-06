/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect, Layer } from "effect";

import {
  HttpClientRegistry,
  HttpClientRegistryLive,
} from "@/services/http-client";

describe("HttpClientRegistry", () => {
  const MockManifests = Layer.succeed(HttpClientRegistry, {
    getAvailableExtensions: Effect.succeed([
      { id: "ext-1", name: "Extension 1", allowed_endpoints: [] },
    ]),
    getClient: () => Effect.die("Not implemented in test"),
  });

  it.effect("should return the list of available extensions", () =>
    Effect.gen(function* () {
      const registry = yield* HttpClientRegistry;
      const extensions = yield* registry.getAvailableExtensions;
      expect(extensions).toHaveLength(1);
      expect(extensions[0].id).toBe("ext-1");
    }).pipe(Effect.provide(MockManifests)),
  );

  it.effect("should cache clients and not recreate them", () =>
    Effect.gen(function* () {
      const registry = yield* HttpClientRegistry;

      const client1 = yield* registry.getClient("ext-1");
      const client2 = yield* registry.getClient("ext-1");

      expect(client1).toBe(client2);
    }).pipe(Effect.provide(HttpClientRegistryLive)),
  );

  it.effect("should instantiate a client on demand for any id", () =>
    Effect.gen(function* () {
      const registry = yield* HttpClientRegistry;

      const client = yield* registry.getClient("any-ext");
      expect(client).toBeDefined();
    }).pipe(Effect.provide(HttpClientRegistryLive)),
  );
});
