/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer, Ref } from "effect";
import { ChartDataRow } from "./types";

const STORAGE_KEY = "curve_buckets_data";

const loadInitialState = (): Record<string, ChartDataRow[]> => {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      return {};
    }
  }
  return {};
};

const persistStore = (newState: Record<string, ChartDataRow[]>) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newState));
};

export class ChartService extends Context.Tag("ChartService")<
  ChartService,
  {
    readonly getSelection: (
      dashboardId: string,
    ) => Effect.Effect<ChartDataRow[]>;
    readonly setSelection: (
      dashboardId: string,
      data: ChartDataRow[],
    ) => Effect.Effect<void>;
    readonly clearSelection: (dashboardId: string) => Effect.Effect<void>;
  }
>() {}

export const ChartServiceLive = Layer.effect(
  ChartService,
  Effect.gen(function* () {
    const stateRef = yield* Ref.make(loadInitialState());

    return ChartService.of({
      getSelection: (dashboardId: string) =>
        Effect.gen(function* () {
          const state = yield* Ref.get(stateRef);
          return state[dashboardId] || [];
        }),

      setSelection: (dashboardId: string, data: ChartDataRow[]) =>
        Effect.gen(function* () {
          yield* Ref.update(stateRef, (state) => {
            const newState = { ...state, [dashboardId]: data };
            persistStore(newState);
            return newState;
          });
        }),

      clearSelection: (dashboardId: string) =>
        Effect.gen(function* () {
          yield* Ref.update(stateRef, (state) => {
            const newState = { ...state, [dashboardId]: [] };
            persistStore(newState);
            return newState;
          });
        }),
    });
  }),
);
