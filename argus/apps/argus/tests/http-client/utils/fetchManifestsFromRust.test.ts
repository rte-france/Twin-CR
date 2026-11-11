/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect } from "effect";
import { mockIPC } from "@tauri-apps/api/mocks";
import { fetchManifestsFromRust } from "@/services/http-client";

describe("fetchManifestsFromRust", () => {
  it.effect(
    "should return an empty array while extension feature is pending",
    () =>
      Effect.gen(function* () {
        const result = yield* fetchManifestsFromRust;
        expect(result).toEqual([]);
      }),
  );

  it.skip(
    "should return manifests on success (TODO: re-enable once Rust IPC get_available_extensions is wired)",
    () =>
      Effect.gen(function* () {
        mockIPC((cmd) => {
          if (cmd === "get_available_extensions") {
            return [{ id: "ext-1", name: "Extension 1", allowed_endpoints: [] }];
          }
        });

        const result = yield* fetchManifestsFromRust;
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe("ext-1");
      }),
  );

  it.skip(
    "should wrap error in TauriInvokeError on failure (TODO: re-enable once Rust IPC get_available_extensions is wired)",
    () =>
      Effect.gen(function* () {
        mockIPC((cmd) => {
          if (cmd === "get_available_extensions") throw new Error("Rust Panic!");
        });

        const error = yield* Effect.flip(fetchManifestsFromRust);
        expect(error._tag).toBe("TauriInvokeError");
        expect(error.method).toBe("get_available_extensions");
      }),
  );
});
