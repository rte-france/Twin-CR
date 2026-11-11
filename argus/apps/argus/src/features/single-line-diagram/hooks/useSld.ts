/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { systemRuntime } from "@/config/runtime";
import { AppMode, Mode } from "@/services/app-mode";
import { GmClient } from "@/services/game-master/service";
import { ScadaClient } from "@/services/scada/service";
import { Console, Effect, Schedule } from "effect";
import { createEffect, createSignal, onCleanup } from "solid-js";
import { Metadata } from "../types/Metadata";

export interface Sld {
  element_id: string;
  metadata: Metadata;
  svg_content?: string;
  svg?: string;
}

export interface SldElement {
  sld: Sld;
  last_sync: number;
}

export const useSld = (equipmentIdAccessor: () => string) => {
  const [sld, setSld] = createSignal<SldElement>();

  createEffect(() => {
    const equipmentId = equipmentIdAccessor();

    if (!equipmentId) return;

    const program = Effect.gen(function* () {
      const appMode = yield* AppMode;
      const mode = yield* appMode.getMode;

      let fetchedRawSld: any;

      switch (mode) {
        case Mode.GameMaster: {
          const gm = yield* GmClient;
          fetchedRawSld = yield* gm.get(`/sld/${equipmentId}`);
          break;
        }
        case Mode.Scada: {
          const scada = yield* ScadaClient;
          fetchedRawSld = yield* scada.get(`/sld/${equipmentId}`);
          break;
        }
      }

      const parsedMetadata =
        typeof fetchedRawSld.metadata === "string"
          ? JSON.parse(fetchedRawSld.metadata)
          : fetchedRawSld.metadata;

      const fetchedSld: Sld = {
        ...fetchedRawSld,
        metadata: parsedMetadata,
      };

      yield* Effect.sync(() => {
        setSld({
          sld: fetchedSld,
          last_sync: Date.now(),
        });
      });
    }).pipe(
      Effect.catchAll((err) =>
        Effect.sync(() =>
          Console.error(`Failed to fetch sld ${equipmentId}`, err),
        ),
      ),
      Effect.repeat(Schedule.spaced("1 seconds")),
    );

    const cancel = systemRuntime.runCallback(program);

    onCleanup(() => cancel());
  });

  return {
    sld,
  };
};
