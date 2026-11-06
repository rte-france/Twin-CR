/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { systemRuntime } from "@/config/runtime";
import type { LobbyError } from "@/services/lobby/error";
import {
  LobbyClient,
  LobbyClientLive,
  type ServerStatus,
} from "@/services/lobby/service";
import { Console, Effect, Exit, Stream } from "effect";
import { createSignal, onCleanup, onMount } from "solid-js";

export const useLobbyUrl = () => {
  const [url, setUrlSignal] = createSignal<string>("");
  const [loading, setLoading] = createSignal<boolean>(true);
  const [error, setError] = createSignal<LobbyError | null>(null);
  const [serverStatus, setServerStatus] =
    createSignal<ServerStatus>("Disconnected");

  const fetchUrl = () => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const lobby = yield* LobbyClient;
      return yield* lobby.getUrl;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit) && exit.cause._tag === "Fail") {
          setError(exit.cause.error as LobbyError);
          Console.error("Failed to fetch Lobby URL", exit.cause.error);
        }
      },
    });
  };

  onMount(() => {
    const program = LobbyClient.pipe(
      Effect.flatMap((lobby) =>
        lobby.statusStream.pipe(
          Stream.runForEach((status) =>
            Effect.sync(() => setServerStatus(status)),
          ),
        ),
      ),
      Effect.provide(LobbyClientLive),
    );

    const cancel = systemRuntime.runCallback(program);
    onCleanup(() => cancel());

    fetchUrl();
  });

  const setUrl = (newUrl: string) => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const lobby = yield* LobbyClient;
      yield* lobby.setUrl(newUrl);
      yield* lobby.connect;
      return newUrl;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit) && exit.cause._tag === "Fail") {
          setError(exit.cause.error as LobbyError);
          Console.error("Failed to set Lobby URL", exit.cause.error);
        }
      },
    });
  };

  const connect = () => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const lobby = yield* LobbyClient;
      yield* lobby.connect;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isFailure(exit) && exit.cause._tag === "Fail") {
          setError(exit.cause.error as LobbyError);
          Console.error("Failed to connect", exit.cause.error);
        }
      },
    });
  };

  const disconnect = () => {
    setLoading(true);
    const program = Effect.gen(function* () {
      const lobby = yield* LobbyClient;
      yield* lobby.disconnect;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isFailure(exit) && exit.cause._tag === "Fail") {
          Console.error("Failed to disconnect", exit.cause.error);
        }
      },
    });
  };

  return {
    url,
    serverStatus,
    loading,
    error,
    setUrl,
    connect,
    disconnect,
    refetch: fetchUrl,
  };
};
