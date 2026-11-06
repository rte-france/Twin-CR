/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer } from "effect";
import { DslClient, type DslError } from "@/services/dsl";
import { invoke } from "@tauri-apps/api/core";

export interface DSLCommandOutput {
  status: string;
  [key: string]: any;
}

export class DslService extends Context.Tag("DslService")<
  DslService,
  {
    readonly getInitialDsl: Effect.Effect<string, DslError>;
    readonly sendDslCommand: (
      text: string,
    ) => Effect.Effect<DSLCommandOutput, DslError>;
  }
>() {}

export const DslServiceLive = Layer.effect(
  DslService,
  Effect.gen(function* () {
    const client = yield* DslClient;

    return {
      getInitialDsl: Effect.gen(function* () {
        const reqId = crypto.randomUUID();
        const endpoint = "/trainer/dsl/initial";

        const getTask = Effect.tryPromise({
          try: () => invoke<string>("get_dsl_text_endpoint", { reqId, endpoint }),
          catch: (error) => error as DslError,
        });

        return yield* getTask.pipe(
          Effect.onInterrupt(() =>
            Effect.tryPromise({
              try: () => invoke("cancel_dsl_task", { reqId }),
              catch: (e) => console.error("Failed to cancel Dsl get task", e),
            }).pipe(Effect.ignore),
          ),
        );
      }),

      sendDslCommand: (text: string) =>
        client.post<DSLCommandOutput>(
          "/trainer/dsl_command",
          text,
          "argus:dsl-editor",  // TODO: put user name as source instead
        ),
    };
  }),
);
