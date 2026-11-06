/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { systemRuntime } from "@/config/runtime";
import type { GmError } from "@/services/game-master/error";
import { GmClient } from "@/services/game-master/service";
import { Console, Effect, Exit } from "effect";
import { createSignal } from "solid-js";

/** Something readable out of a GmError, whichever variant it is. */
export const describeGmError = (error: GmError): string => {
  if ("reason" in error && error.reason) {
    return error.reason;
  }
  if (error.message) {
    return error.message;
  }
  return "_tag" in error ? error._tag : "unknown error";
};

export const useGmControls = () => {
  const [loading, setLoading] = createSignal<boolean>(false);
  const [error, setError] = createSignal<GmError | null>(null);

  /**
   * Whether the orchestrator accepted the command.
   *
   * Resolves rather than returning the canceller, so a caller can wait for the
   * outcome before telling the user it happened.
   */
  const sendCommand = (endpoint: string, commandName: string): Promise<boolean> =>
    new Promise((resolve) => {
      setLoading(true);
      setError(null);

      const program = Effect.gen(function* () {
        const gm = yield* GmClient;
        return yield* gm.post(endpoint, "{}");
      });

      systemRuntime.runCallback(program, {
        onExit: (exit) => {
          setLoading(false);
          if (Exit.isSuccess(exit)) {
            Console.log(`Successfully executed: ${commandName}`);
            resolve(true);
            return;
          }
          const failure =
            exit.cause._tag === "Fail"
              ? (exit.cause.error as GmError)
              : new Error(`${commandName} did not complete (${exit.cause._tag})`);
          setError(failure);
          Console.error(`Failed to execute ${commandName}`, failure);
          resolve(false);
        },
      });
    });

  const start = () => sendCommand("/start", "start");
  const pause = () => sendCommand("/pause?requester=trainer", "pause");
  const resume = () => sendCommand("/resume?requester=trainer", "resume");
  const stop = () => sendCommand("/stop?requester=trainer", "stop");

  return {
    start,
    pause,
    resume,
    stop,
    loading,
    error,
  };
};
