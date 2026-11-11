/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { Effect, Stream } from "effect";
import { AppMode, Mode } from "@/services/app-mode";
import { systemRuntime } from "@/config/runtime";

const [mode, setModeSignal] = createSignal<Mode>(Mode.GameMaster);

const syncProgram = Effect.gen(function* () {
  const appMode = yield* AppMode;

  return yield* appMode.modeStream.pipe(
    Stream.runForEach((newMode) => Effect.sync(() => setModeSignal(newMode))),
  );
});

systemRuntime.runCallback(syncProgram);

export const useAppMode = () => {
  const setMode = (newMode: Mode) => {
    setModeSignal(newMode);

    const program = Effect.gen(function* () {
      const appMode = yield* AppMode;
      yield* appMode.setMode(newMode);
    });

    systemRuntime.runPromise(program).catch((e) => {
      console.error("Failed to save the current mode:", e);
    });
  };

  return [mode, setMode] as const;
};
