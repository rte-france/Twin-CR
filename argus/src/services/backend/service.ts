/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer } from "effect";
import { Exit, Cause } from "effect";
import { GmClient } from "@/services/game-master/service";
import { ScadaClient } from "@/services/scada/service";
import { AppMode, Mode } from "@/services/app-mode/service";
import { systemRuntime } from "@/config/runtime";

export interface BackendService {
  readonly get: <T = any>(endpoint: string) => Effect.Effect<T>;
  readonly post: <T = any>(endpoint: string, body: unknown) => Effect.Effect<T>;
}

export class Backend extends Context.Tag("Backend")<Backend, BackendService>() {}

export const BackendLive = Layer.effect(
  Backend,
  Effect.gen(function* () {
    const appMode = yield* AppMode;
    const gmClient = yield* GmClient;
    const scadaClient = yield* ScadaClient;

    return Backend.of({
      get: <T>(endpoint: string) =>
        Effect.gen(function* () {
          const mode = yield* appMode.getMode;
          const effect = mode === Mode.Scada
            ? scadaClient.get<T>(endpoint)
            : gmClient.get<T>(endpoint);
          return yield* effect;
        }).pipe(Effect.orDie),

      post: <T>(endpoint: string, body: unknown) =>
        Effect.gen(function* () {
          const mode = yield* appMode.getMode;
          const effect = mode === Mode.Scada
            ? scadaClient.post<T>(endpoint, JSON.stringify(body))
            : gmClient.post<T>(endpoint, JSON.stringify(body));
          return yield* effect;
        }).pipe(Effect.orDie),
    });
  }),
);

// ── Simple promise helpers with default error handling

function runBackend<T>(effect: Effect.Effect<T, any, Backend>): Promise<T> {
  return new Promise((resolve, reject) => {
    systemRuntime.runCallback(effect, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit)) resolve(exit.value as T);
        else reject(new Error(Cause.pretty(exit.cause)));
      },
    });
  });
}

export function backendGet<T>(endpoint: string): Promise<T> {
  return runBackend(
    Effect.gen(function* () {
      const backend = yield* Backend;
      return yield* backend.get<T>(endpoint);
    }),
  );
}

export function backendPost<T>(endpoint: string, body: unknown): Promise<T> {
  return runBackend(
    Effect.gen(function* () {
      const backend = yield* Backend;
      return yield* backend.post<T>(endpoint, body);
    }),
  );
}
