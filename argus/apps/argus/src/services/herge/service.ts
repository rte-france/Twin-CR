/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { invoke } from "@tauri-apps/api/core";
import { Context, Effect, Layer } from "effect";

import { parseTauriError, type HergeError } from "./error";

export class HergeClient extends Context.Tag("HergeClient")<
  HergeClient,
  {
    readonly setUrl: (newUrl: string) => Effect.Effect<void, HergeError>;
    readonly fetch: (url: string) => Effect.Effect<Uint8Array, HergeError>;
  }
>() {}

export const HergeClientLive = Layer.succeed(
  HergeClient,
  HergeClient.of({
    setUrl: (newUrl) =>
      Effect.tryPromise({
        try: () => invoke<void>("set_herge_url", { newUrl }),
        catch: parseTauriError,
      }),
    fetch: (url) =>
      Effect.gen(function* () {
        const reqId = crypto.randomUUID();

        const fetchTask = Effect.tryPromise({
          try: () => invoke<Uint8Array>("fetch_request", { url, reqId }),
          catch: parseTauriError,
        });

        return yield* fetchTask.pipe(
          Effect.onInterrupt(() =>
            Effect.tryPromise({
              try: () => invoke("cancel_request", { reqId }),
              catch: (e) => console.error("Failed to send abort signal", e),
            }).pipe(Effect.ignore),
          ),
        );
      }),
  }),
);
