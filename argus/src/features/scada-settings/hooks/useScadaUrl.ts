/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { systemRuntime } from "@/config/runtime";
import type { ScadaError } from "@/services/scada/error";
import {
  ScadaClient,
  ScadaClientLive,
  type ServerStatus,
} from "@/services/scada/service";
import { Console, Effect, Exit, Stream } from "effect";
import { createSignal, onCleanup, onMount } from "solid-js";

export const useGmUrl = () => {
  const [url, setUrlSignal] = createSignal<string>("");
  const [loading, setLoading] = createSignal<boolean>(true);
  const [error, setError] = createSignal<ScadaError | null>(null);
  const [serverStatus, setServerStatus] =
    createSignal<ServerStatus>("Disconnected");

  const fetchUrl = () => {
    setLoading(true);
    setError(null);

    const program = Effect.gen(function* () {
      const scada = yield* ScadaClient;
      return yield* scada.getUrl;
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit)) {
          if (exit.cause._tag === "Fail") {
            setError(exit.cause.error as ScadaError);
            Console.error("Failed to fetch GM URL", exit.cause.error);
          }
        }
      },
    });
  };

  onMount(() => {
    const program = ScadaClient.pipe(
      Effect.flatMap((scada) =>
        scada.statusStream.pipe(
          Stream.runForEach((status) =>
            Effect.sync(() => setServerStatus(status)),
          ),
        ),
      ),
      Effect.provide(ScadaClientLive),
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
      const scada = yield* ScadaClient;

      yield* scada.setUrl(newUrl);
      yield* scada.connect;

      return newUrl;
    });

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLoading(false);
        if (Exit.isSuccess(exit)) {
          setUrlSignal(exit.value);
        } else if (Exit.isFailure(exit)) {
          if (exit.cause._tag === "Fail") {
            setError(exit.cause.error as ScadaError);
            Console.error("Failed to set GM URL", exit.cause.error);
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
