/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { invoke } from "@tauri-apps/api/core";
import { Context, Effect, Layer, Stream } from "effect";
import { parseLobbyError, type LobbyError, type DslTask } from "./error";
import { listen } from "@tauri-apps/api/event";

export type ServerStatus =
  | "Connecting"
  | "Healthy"
  | "Disconnected"
  | { Degraded: number };

export interface LobbyClientService {
  readonly setUrl: (url: string) => Effect.Effect<void, LobbyError>;
  readonly getUrl: Effect.Effect<string, LobbyError>;
  readonly getStatus: Effect.Effect<string, LobbyError>;
  readonly connect: Effect.Effect<void, LobbyError>;
  readonly disconnect: Effect.Effect<void, LobbyError>;
  readonly getTasks: Effect.Effect<DslTask[], LobbyError>;
  readonly get: <T = any>(endpoint: string) => Effect.Effect<T, LobbyError>;
  readonly statusStream: Stream.Stream<ServerStatus, LobbyError>;
}

export class LobbyClient extends Context.Tag("LobbyClient")<
  LobbyClient,
  LobbyClientService
>() {}

export const LobbyClientLive = Layer.succeed(
  LobbyClient,
  LobbyClient.of({
    setUrl: (url) =>
      Effect.tryPromise({
        try: () => invoke<void>("set_lobby_url", { url }),
        catch: parseLobbyError,
      }),

    getUrl: Effect.tryPromise({
      try: () => invoke<string>("get_lobby_url"),
      catch: parseLobbyError,
    }),

    getStatus: Effect.tryPromise({
      try: () => invoke<string>("get_lobby_status"),
      catch: parseLobbyError,
    }),

    connect: Effect.tryPromise({
      try: () => invoke<void>("connect_lobby"),
      catch: parseLobbyError,
    }),

    disconnect: Effect.tryPromise({
      try: () => invoke<void>("disconnect_lobby"),
      catch: parseLobbyError,
    }),

    getTasks: Effect.tryPromise({
      try: () => invoke<DslTask[]>("get_lobby_tasks"),
      catch: parseLobbyError,
    }),

    get: <T = any>(endpoint: string) =>
      Effect.gen(function* () {
        const reqId = crypto.randomUUID();

        const getTask = Effect.tryPromise({
          try: () => invoke<T>("get_lobby_endpoint", { reqId, endpoint }),
          catch: parseLobbyError,
        });

        return yield* getTask.pipe(
          Effect.onInterrupt(() =>
            Effect.tryPromise({
              try: () => invoke("cancel_lobby_task", { reqId }),
              catch: (e) => console.error("Failed to cancel Lobby GET task", e),
            }).pipe(Effect.ignore),
          ),
        );
      }),

    statusStream: Stream.async<ServerStatus, LobbyError>((emit) => {
      invoke<ServerStatus>("get_lobby_status")
        .then((s) => emit.single(s))
        .catch((e) => emit.fail(parseLobbyError(e)));

      const unlistenPromise = listen<ServerStatus>(
        "lobby-status-update",
        (event) => {
          emit.single(event.payload);
        },
      );

      return Effect.promise(async () => {
        const unlisten = await unlistenPromise;
        unlisten();
      });
    }),
  }),
);
