/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, onCleanup, onMount, type Accessor } from "solid-js";
import { Effect, Exit } from "effect";
import { systemRuntime } from "@/config/runtime";
import { ArcGisService } from "../services/arcgis";
import type { Extent } from "../types";

export function useArcGis(
  activeService: Accessor<string>,
  selectedSchema: Accessor<string | null>,
  setExtent: (extent: Extent) => void
) {
  const [schemasList, setSchemasList] = createSignal<readonly string[]>([]);
  const [legendData, setLegendData] = createSignal<readonly any[]>([]);
  const [legendLoading, setLegendLoading] = createSignal(false);
  const [legendError, setLegendError] = createSignal<string | null>(null);

  onMount(() => {
    const program = Effect.gen(function* () {
      const arcgis = yield* ArcGisService;
      return yield* arcgis.fetchSchemasList;
    }).pipe(
      Effect.catchAll((err) => {
        console.error("Failed to fetch schemas list", err);
        return Effect.succeed([]);
      })
    );

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit)) setSchemasList(exit.value);
      },
    });

    onCleanup(() => cancel());
  });

  createEffect(() => {
    const name = selectedSchema();
    if (!name) return;

    const program = Effect.gen(function* () {
      const arcgis = yield* ArcGisService;
      return yield* arcgis.fetchSchemaExtent(name);
    }).pipe(
      Effect.catchAll((err) => {
        console.error(`Failed to fetch extent for schema ${name}`, err);
        return Effect.succeed(null);
      })
    );

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit) && exit.value !== null) {
          setExtent(exit.value);
        }
      },
    });

    onCleanup(() => cancel());
  });

  createEffect(() => {
    const serviceId = activeService();
    setLegendLoading(true);
    setLegendError(null);

    const program = Effect.gen(function* () {
      const arcgis = yield* ArcGisService;
      return yield* arcgis.fetchLegend(serviceId);
    });

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setLegendLoading(false);
        if (Exit.isSuccess(exit)) {
          setLegendData(exit.value);
        } else {
          setLegendError("Failed to load legend");
          setLegendData([]);
        }
      },
    });

    onCleanup(() => cancel());
  });

  return {
    schemasList,
    legendData,
    legendLoading,
    legendError,
  };
}
