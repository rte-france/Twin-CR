/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer, SubscriptionRef, Stream } from "effect";
import { WindowManager } from "@/services/window-manager";

export const Mode = {
  GameMaster: "GameMaster",
  Scada: "Scada",
} as const;

export type Mode = (typeof Mode)[keyof typeof Mode];

export interface AppModeService {
  readonly getMode: Effect.Effect<Mode>;
  readonly setMode: (mode: Mode) => Effect.Effect<void>;
  readonly modeStream: Stream.Stream<Mode>;
}

export class AppMode extends Context.Tag("AppMode")<
  AppMode,
  AppModeService
>() {}

export const AppModeLive = Layer.scoped(
  AppMode,
  Effect.gen(function* () {
    const wm = yield* WindowManager;
    const windowLabel = yield* wm.getCurrentLabel();
    const STORAGE_KEY = `argus:app-mode-${windowLabel}`;

    const initialMode =
      (localStorage.getItem(STORAGE_KEY) as Mode) || Mode.GameMaster;

    const ref = yield* SubscriptionRef.make<Mode>(initialMode);

    yield* ref.changes.pipe(
      Stream.runForEach((mode) =>
        Effect.sync(() => localStorage.setItem(STORAGE_KEY, mode)),
      ),
      Effect.forkScoped,
    );

    return AppMode.of({
      getMode: SubscriptionRef.get(ref),
      setMode: (mode: Mode) => SubscriptionRef.set(ref, mode),
      modeStream: ref.changes,
    });
  }),
);
