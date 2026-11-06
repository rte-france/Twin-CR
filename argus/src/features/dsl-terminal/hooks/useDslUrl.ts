/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { systemRuntime } from "@/config/runtime";
import type { DslError } from "@/services/dsl/error";
import {
  DslClient,
  DslClientLive,
  type ServerStatus,
} from "@/services/dsl/service";
import { Console, Effect, Exit, Stream } from "effect";
import { createSignal, onCleanup, onMount } from "solid-js";

export const useDslUrl = () => {
  const [url, setUrlSignal] = createSignal<string>("");
  const [loading, setLoading] = createSignal<boolean>(true);
  const [error, setError] = createSignal<DslError | null>(null);
  const [serverStatus, setServerStatus] =
    createSignal<ServerStatus>("Disconnected");

  const fetchUrl = () => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const dsl = yield* DslClient;
      return yield* dsl.getUrl;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit)) {
          if (exit.cause._tag === "Fail") {
            setError(exit.cause.error as DslError);
            Console.error("Failed to fetch DSL URL", exit.cause.error);
          }
        }
      },
    });
  };

  onMount(() => {
    const program = DslClient.pipe(
      Effect.flatMap((dsl) =>
        dsl.statusStream.pipe(
          Stream.runForEach((status) =>
            Effect.sync(() => setServerStatus(status)),
          ),
        ),
      ),
      Effect.provide(DslClientLive),
    );

    const cancel = systemRuntime.runCallback(program);

    onCleanup(() => cancel());
  });

  onMount(() => {
    fetchUrl();
  });

  const setUrl = (newUrl: string) => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const dsl = yield* DslClient;

      yield* dsl.setUrl(newUrl);
      yield* dsl.connect;

      return newUrl;
    });

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit)) {
          if (exit.cause._tag === "Fail") {
            setError(exit.cause.error as DslError);
            Console.error("Failed to set DSL URL", exit.cause.error);
          }
        }
      },
    });

    return cancel;
  };

  return {
    url,
    serverStatus,
    loading,
    error,
    setUrl,
    refetch: fetchUrl,
  };
};
