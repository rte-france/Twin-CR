/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer, Ref, Either, Stream, Schedule } from "effect";
import { GmClient } from "@/services/game-master/service";
import { AppMode, Mode } from "@/services/app-mode";
import { ScadaClient } from "@/services/scada/service";
import { GmError } from "../game-master/error";
import { ScadaError } from "../scada/error";
import { EstimState, EstimVariable, MappingState } from "./types";

export class MappingService extends Context.Tag("MappingService")<
  MappingService,
  {
    readonly getState: Effect.Effect<MappingState>;
    readonly getEstimState: Effect.Effect<EstimState>;
    readonly fetch: (
      force?: boolean,
    ) => Effect.Effect<
      void,
      GmError | ScadaError,
      AppMode | GmClient | ScadaClient
    >;
  }
>() {}

export const MappingServiceLive = Layer.scoped(
  MappingService,
  Effect.gen(function* () {
    const appMode = yield* AppMode;
    const gm = yield* GmClient;
    const scada = yield* ScadaClient;

    const stateRef = yield* Ref.make<MappingState>({
      data: [],
      isLoading: false,
      error: null,
      activeMode: null,
    });

    const stateEstimRef = yield* Ref.make<EstimState>({
      data: [],
      isLoading: false,
      error: null,
      activeMode: null,
    });

    const fetch = (force = false) =>
      Effect.gen(function* () {
        const currentMode = yield* appMode.getMode;
        const state = yield* Ref.get(stateRef);
        const estimState = yield* Ref.get(stateEstimRef);

        const isModeChanged = state.activeMode !== currentMode;
        const shouldFetch = force || isModeChanged || state.data.length === 0;

        if (!shouldFetch || state.isLoading || estimState.isLoading) {
          return;
        }

        yield* Ref.update(stateRef, (s) => ({
          ...s,
          isLoading: true,
          error: null,
        }));

        yield* Ref.update(stateEstimRef, (s) => ({
          ...s,
          isLoading: true,
          error: null,
        }));

        const fetchTask =
          currentMode === Mode.GameMaster
            ? gm.get("/mapping")
            : scada.get("/mapping");

        const result = yield* Effect.either(fetchTask);

        if (Either.isRight(result)) {
          yield* Ref.set(stateRef, {
            data: (result.right as any[]).map((item) => ({ ...item, side: item.side ?? null })),  // Enforce side=null if undefined
            isLoading: false,
            error: null,
            activeMode: currentMode,
          });
        } else {
          yield* Ref.set(stateRef, {
            data: [],
            isLoading: false,
            error: new Error(`Load failed: ${result.left}`),
            activeMode: currentMode,
          });
        }

        const resultEstim = yield* Effect.either(
          scada.get<EstimVariable[]>("/estim-variables"),
        );

        if (Either.isRight(resultEstim)) {
          yield* Ref.set(stateEstimRef, {
            data: resultEstim.right,
            isLoading: false,
            error: null,
            activeMode: currentMode,
          });
        } else {
          yield* Ref.set(stateEstimRef, {
            data: [],
            isLoading: false,
            error: new Error(`Load failed: ${resultEstim.left}`),
            activeMode: currentMode,
          });
        }
      });

    yield* fetch();

    yield* Effect.forkScoped(
      Stream.runForEach(appMode.modeStream, () => fetch()),
    );

    yield* Effect.forkScoped(
      Effect.repeat(
        Effect.gen(function* () {
          const state = yield* Ref.get(stateRef);
          if (state.error || state.data.length === 0) {
            yield* fetch(true);
          }
        }),
        Schedule.spaced("5 seconds"),
      ),
    );

    return MappingService.of({
      getState: Ref.get(stateRef),
      getEstimState: Ref.get(stateEstimRef),
      fetch,
    });
  }),
);
