/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Channel, invoke } from "@tauri-apps/api/core";
import { Context, Effect, Layer, Stream } from "effect";
import { parseGmError, type GmError, type GmTask } from "./error";
import { listen } from "@tauri-apps/api/event";

export type ServerStatus =
  | "Connecting"
  | "Healthy"
  | "Disconnected"
  | { Degraded: number };

type SseMessage<T> = { type: "Chunk"; data: T } | { type: "Closed" };

export interface GmSseData {
  id: string;
  value: number;
  time: number;
}

export interface GmHistoryItem {
  id: string;
  value: number;
  time: number;
}

export interface GmClientService {
  readonly setUrl: (url: string) => Effect.Effect<void, GmError>;
  readonly getUrl: Effect.Effect<string, GmError>;
  readonly getStatus: Effect.Effect<string, GmError>;
  readonly connect: Effect.Effect<void, GmError>;
  readonly disconnect: Effect.Effect<void, GmError>;
  readonly getTasks: Effect.Effect<GmTask[], GmError>;
  readonly get: <T = any>(endpoint: string) => Effect.Effect<T, GmError>;
  readonly post: <T = any>(
    endpoint: string,
    body: string,
  ) => Effect.Effect<T, GmError>;
  readonly statusStream: Stream.Stream<ServerStatus, GmError>;
  readonly sseStream: <T = GmSseData>(
    endpoint: string,
  ) => Stream.Stream<T, GmError>;
}

export class GmClient extends Context.Tag("GmClient")<
  GmClient,
  GmClientService
>() {}

export const GmClientLive = Layer.succeed(
  GmClient,
  GmClient.of({
    setUrl: (url) =>
      Effect.tryPromise({
        try: () => invoke<void>("set_gm_url", { url }),
        catch: parseGmError,
      }),

    getUrl: Effect.tryPromise({
      try: () => invoke<string>("get_gm_url"),
      catch: parseGmError,
    }),

    getStatus: Effect.tryPromise({
      try: () => invoke<string>("get_gm_status"),
      catch: parseGmError,
    }),

    connect: Effect.tryPromise({
      try: () => invoke<void>("connect_gm"),
      catch: parseGmError,
    }),

    disconnect: Effect.tryPromise({
      try: () => invoke<void>("disconnect_gm"),
      catch: parseGmError,
    }),

    getTasks: Effect.tryPromise({
      try: () => invoke<GmTask[]>("get_gm_tasks"),
      catch: parseGmError,
    }),

    get: <T = any>(endpoint: string) =>
      Effect.gen(function* () {
        const reqId = crypto.randomUUID();

        const getTask = Effect.tryPromise({
          try: () => invoke<T>("get_gm_endpoint", { reqId, endpoint }),
          catch: parseGmError,
        });

        return yield* getTask.pipe(
          Effect.onInterrupt(() =>
            Effect.tryPromise({
              try: () => invoke("cancel_gm_task", { reqId }),
              catch: (e) => console.error("Failed to cancel GM task", e),
            }).pipe(Effect.ignore),
          ),
        );
      }),

    post: <T = any>(endpoint: string, body: string) =>
      Effect.gen(function* () {
        const reqId = crypto.randomUUID();

        const postTask = Effect.tryPromise({
          try: () => invoke<T>("post_gm_endpoint", { reqId, endpoint, body }),
          catch: parseGmError,
        });

        return yield* postTask.pipe(
          Effect.onInterrupt(() =>
            Effect.tryPromise({
              try: () => invoke("cancel_gm_task", { reqId }),
              catch: (e) => console.error("Failed to cancel GM POST task", e),
            }).pipe(Effect.ignore),
          ),
        );
      }),

    statusStream: Stream.async<ServerStatus, GmError>((emit) => {
      invoke<ServerStatus>("get_gm_status")
        .then((s) => emit.single(s))
        .catch((e) => emit.fail(parseGmError(e)));

      const unlistenPromise = listen<ServerStatus>(
        "gm-status-update",
        (event) => {
          emit.single(event.payload);
        },
      );

      return Effect.promise(async () => {
        const unlisten = await unlistenPromise;
        unlisten();
      });
    }),

    sseStream: <T = GmSseData>(endpoint: string) =>
      Stream.async<T, GmError>((emit) => {
        const reqId = crypto.randomUUID();

        const onEvent = new Channel<SseMessage<T>>();

        onEvent.onmessage = (message) => {
          if (message.type === "Chunk") {
            emit.single(message.data);
          } else if (message.type === "Closed") {
            emit.end();
          }
        };

        invoke("start_gm_sse", { reqId, endpoint, onEvent }).catch((e) => {
          emit.fail(parseGmError(e));
        });

        return Effect.tryPromise({
          try: () => invoke("cancel_gm_task", { reqId }),
          catch: (e) => e,
        }).pipe(
          Effect.catchAll((e) =>
            Effect.sync(() => console.error("Failed to cancel GM SSE task", e)),
          ),
        );
      }),
  }),
);
