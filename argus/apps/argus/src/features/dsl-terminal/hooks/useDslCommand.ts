/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { Console, Effect, Exit } from "effect";
import { systemRuntime } from "@/config/runtime";
import { DslClient } from "@/services/dsl/service";
import { SystemDead, type DslError } from "@/services/dsl/error";
import { DSLAutocompleteResponse } from "../types";

export function useDslCommand() {
  const [isLoading, setIsLoading] = createSignal(false);
  const [error, setError] = createSignal<DslError | null>(null);
  const [isSuccess, setIsSuccess] = createSignal(false);

  const sendCommand = (dslText: string) => {
    setIsLoading(true);
    setError(null);
    setIsSuccess(false);

    const program = Effect.gen(function* () {
      const client = yield* DslClient;
      return yield* client.post(
        "/trainer/dsl_command",
        dslText,
        "argus:dsl-terminal",  // TODO: put user name as source instead
      );
    });

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setIsLoading(false);

        if (Exit.isSuccess(exit)) {
          setIsSuccess(true);
        } else if (Exit.isFailure(exit)) {
          Console.error("Exit Failure:", exit.cause);

          if (exit.cause._tag === "Fail") {
            setError(exit.cause.error as DslError);
          } else {
            setError(
              new SystemDead({
                reason: `Unexpected Crash: ${String(exit.cause)}`,
              }),
            );
          }
        }
      },
    });

    return cancel;
  };

  const dslAutocomplete = (
    command: string,
    onSuccess: (data: DSLAutocompleteResponse) => void,
  ) => {
    const program = Effect.gen(function* () {
      const client = yield* DslClient;
      return yield* client.post("/completion", command, "argus:dsl-terminal");
    });

    return systemRuntime.runCallback(program, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit)) {
          onSuccess(exit.value as DSLAutocompleteResponse);
        } else if (Exit.isFailure(exit)) {
          Console.error("Autocomplete Failure:", exit.cause);
        }
      },
    });
  };

  return { sendCommand, dslAutocomplete, isLoading, error, isSuccess };
}
