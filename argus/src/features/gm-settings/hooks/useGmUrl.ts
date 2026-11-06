/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { systemRuntime } from "@/config/runtime";
import type { GmError } from "@/services/game-master/error";
import {
  GmClient,
  GmClientLive,
  type ServerStatus,
} from "@/services/game-master/service";
import { Console, Effect, Exit, Stream } from "effect";
import { createSignal, onCleanup, onMount } from "solid-js";

export const useGmUrl = () => {
  const [url, setUrlSignal] = createSignal<string>("");
  const [loading, setLoading] = createSignal<boolean>(true);
  const [error, setError] = createSignal<GmError | null>(null);
  const [serverStatus, setServerStatus] =
    createSignal<ServerStatus>("Disconnected");

  const fetchUrl = () => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const gm = yield* GmClient;
      return yield* gm.getUrl;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit)) {
          if (exit.cause._tag === "Fail") {
            setError(exit.cause.error as GmError);
            Console.error("Failed to fetch GM URL", exit.cause.error);
          }
        }
      },
    });
  };

  onMount(() => {
    const program = GmClient.pipe(
      Effect.flatMap((gm) =>
        gm.statusStream.pipe(
          Stream.runForEach((status) =>
            Effect.sync(() => setServerStatus(status)),
          ),
        ),
      ),
      Effect.provide(GmClientLive),
    );

    const cancel = systemRuntime.runCallback(program);
    onCleanup(() => cancel());

    fetchUrl();
  });

  const setUrl = (newUrl: string) => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const gm = yield* GmClient;
      yield* gm.setUrl(newUrl);
      yield* gm.connect;
      return newUrl;
    });

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit)) {
          if (exit.cause._tag === "Fail") {
            setError(exit.cause.error as GmError);
            Console.error("Failed to set GM URL", exit.cause.error);
          }
        }
      },
    });

    return cancel;
  };

  const connect = () => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const gm = yield* GmClient;
      yield* gm.connect;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isFailure(exit) && exit.cause._tag === "Fail") {
          setError(exit.cause.error as GmError);
          Console.error("Failed to connect", exit.cause.error);
        }
      },
    });
  };

  const disconnect = () => {
    setLoading(true);
    const program = Effect.gen(function* () {
      const gm = yield* GmClient;
      yield* gm.disconnect;
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
