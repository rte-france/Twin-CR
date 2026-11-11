/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Channel, invoke } from "@tauri-apps/api/core";
import { Context, Effect, Layer, Stream } from "effect";
import { parseScadaError, type ScadaError, type GmTask } from "./error";
import { listen } from "@tauri-apps/api/event";

export type ServerStatus =
  | "Connecting"
  | "Healthy"
  | "Disconnected"
  | { Degraded: number };

type SseMessage<T> = { type: "Chunk"; data: T } | { type: "Closed" };

export interface ScadaSseData {
  id: string;
  value: number;
  time_sent: number;
  time_received: number;
}

export interface ScadaHistoryItem {
  id: string;
  value: number;
  time_received: number;
}

export interface EstimItem {
  equipmentId: string;
  kind: string;
  side: string | null;
  value: number;
  time: number;
  topic: string;
}

export class ScadaClient extends Context.Tag("ScadaClient")<
  ScadaClient,
  {
    readonly setUrl: (url: string) => Effect.Effect<void, ScadaError>;
    readonly getUrl: Effect.Effect<string, ScadaError>;
    readonly getStatus: Effect.Effect<string, ScadaError>;
    readonly connect: Effect.Effect<void, ScadaError>;
    readonly getTasks: Effect.Effect<GmTask[], ScadaError>;
    readonly get: <T = any>(endpoint: string) => Effect.Effect<T, ScadaError>;
    readonly post: <T = any>(
      endpoint: string,
      body: string,
    ) => Effect.Effect<T, ScadaError>;
    readonly statusStream: Stream.Stream<ServerStatus, ScadaError>;
    readonly sseStream: <T = ScadaSseData>(
      endpoint: string,
    ) => Stream.Stream<T, ScadaError>;
  }
>() {}

export const ScadaClientLive = Layer.succeed(
  ScadaClient,
  ScadaClient.of({
    setUrl: (url) =>
      Effect.tryPromise({
        try: () => invoke<void>("set_scada_url", { url }),
        catch: parseScadaError,
      }),

    getUrl: Effect.tryPromise({
      try: () => invoke<string>("get_scada_url"),
      catch: parseScadaError,
    }),

    getStatus: Effect.tryPromise({
      try: () => invoke<string>("get_scada_status"),
      catch: parseScadaError,
    }),

    connect: Effect.tryPromise({
      try: () => invoke<void>("connect_scada"),
      catch: parseScadaError,
    }),

    getTasks: Effect.tryPromise({
      try: () => invoke<GmTask[]>("get_scada_tasks"),
      catch: parseScadaError,
    }),

    get: <T = any>(endpoint: string) =>
      Effect.gen(function* () {
        const reqId = crypto.randomUUID();

        const getTask = Effect.tryPromise({
          try: () => invoke<T>("get_scada_endpoint", { reqId, endpoint }),
          catch: parseScadaError,
        });

        return yield* getTask.pipe(
          Effect.onInterrupt(() =>
            Effect.tryPromise({
              try: () => invoke("cancel_scada_task", { reqId }),
              catch: (e) => console.error("Failed to cancel SCADA task", e),
            }).pipe(Effect.ignore),
          ),
        );
      }),

    post: <T = any>(endpoint: string, body: string) =>
      Effect.gen(function* () {
        const reqId = crypto.randomUUID();

        const postTask = Effect.tryPromise({
          try: () =>
            invoke<T>("post_scada_endpoint", { reqId, endpoint, body }),
          catch: parseScadaError,
        });

        return yield* postTask.pipe(
          Effect.onInterrupt(() =>
            Effect.tryPromise({
              try: () => invoke("cancel_scada_task", { reqId }),
              catch: (e) =>
                console.error("Failed to cancel SCADA POST task", e),
            }).pipe(Effect.ignore),
          ),
        );
      }),

    statusStream: Stream.async<ServerStatus, ScadaError>((emit) => {
      invoke<ServerStatus>("get_scada_status")
        .then((s) => emit.single(s))
        .catch((e) => emit.fail(parseScadaError(e)));

      const unlistenPromise = listen<ServerStatus>(
        "scada-status-update",
        (event) => {
          emit.single(event.payload);
        },
      );

      return Effect.promise(async () => {
        const unlisten = await unlistenPromise;
        unlisten();
      });
    }),

    sseStream: <T = ScadaSseData>(endpoint: string) =>
      Stream.async<T, ScadaError>((emit) => {
        const reqId = crypto.randomUUID();

        const onEvent = new Channel<SseMessage<T>>();

        onEvent.onmessage = (message) => {
          if (message.type === "Chunk") {
            emit.single(message.data);
          } else if (message.type === "Closed") {
            emit.end();
          }
        };

        invoke("start_scada_sse", { reqId, endpoint, onEvent }).catch((e) => {
          emit.fail(parseScadaError(e));
        });

        return Effect.tryPromise({
          try: () => invoke("cancel_scada_task", { reqId }),
          catch: (e) => e,
        }).pipe(
          Effect.catchAll((e) =>
            Effect.sync(() =>
              console.error("Failed to cancel Scada SSE task", e),
            ),
          ),
        );
      }),
  }),
);
