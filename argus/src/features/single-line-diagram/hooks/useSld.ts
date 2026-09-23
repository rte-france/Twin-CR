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
import { Effect, Schedule } from "effect";
import { createEffect, createSignal, onCleanup } from "solid-js";
import { Metadata } from "../types/Metadata";
import type { SldDiagramParams } from "../types/SldDiagram";

export interface Sld {
  metadata: Metadata;
  svg_content?: string;
  svg?: string;
}

export interface SldElement {
  sld: Sld;
  last_sync: number;
}

const requestBody = (params: SldDiagramParams) => {
  const body: Record<string, unknown> = {
    substations: params.elements.filter((e) => e.type === "sub").map((e) => e.id),
    voltage_levels: params.elements.filter((e) => e.type === "vl").map((e) => e.id),
  };

  if (params.elements.length > 1) {
    body.layout_parameters =
      params.layoutType === "matrix"
        ? { layout_type: "matrix", matrix: params.matrix }
        : {
            layout_type: "positioned",
            positions: params.elements.map((e) => ({
              id: e.id,
              x: params.positions[e.id]?.x ?? 0,
              y: params.positions[e.id]?.y ?? 0,
            })),
          };
  }
  return JSON.stringify(body);
};

export const useSld = (paramsAccessor: () => SldDiagramParams) => {
  const [sld, setSld] = createSignal<SldElement>();

  createEffect(() => {
    const params = paramsAccessor();

    if (params.elements.length === 0) return;

    const body = requestBody(params);

    const program = Effect.gen(function* () {
      const appMode = yield* AppMode;
      const mode = yield* appMode.getMode;

      let fetchedRawSld: any;

      switch (mode) {
        case Mode.GameMaster: {
          const gm = yield* GmClient;
          fetchedRawSld = yield* gm.post("/sld", body);
          break;
        }
        case Mode.Scada: {
          const scada = yield* ScadaClient;
          fetchedRawSld = yield* scada.post("/sld", body);
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
          console.error(`Failed to fetch sld ${body}`, err),
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
