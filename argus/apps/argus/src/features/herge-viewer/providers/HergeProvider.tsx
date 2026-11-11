/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, createSignal, on, type ParentComponent } from "solid-js";
import { createStoredSignal } from "@/hooks/createStoreSignal";
import type { Extent } from "../types";
import { DEFAULT_VISIBILITY, SCHEMATIC_EXTENT, SERVICES } from "../config";
import { useArcGis } from "../hooks/useArcGis";
import { HergeContext } from "./HergeContext";
import { Effect, Exit } from "effect";
import { ArcGisService } from "../services/arcgis";
import { systemRuntime } from "@/config/runtime";

interface HergeProviderProps {
  selectedSchema?: string;
}

export const HergeProvider: ParentComponent<HergeProviderProps> = (props) => {
  const prefix = props.selectedSchema || "default";

  const [extent, setExtent] = createStoredSignal<Extent>(
    `herge_extent_${prefix}`,
    { ...SCHEMATIC_EXTENT },
  );

  const [visibility, setVisibility] = createStoredSignal<
    Record<string, boolean>
  >(`herge_visibility_${prefix}`, DEFAULT_VISIBILITY);

  const [activeService, setActiveService] = createSignal<string>(
    SERVICES[0].id,
  );
  const [loading, setLoading] = createSignal(false);
  const [selectedSchema, setSelectedSchema] = createSignal<string | null>(
    props.selectedSchema || null,
  );

  const { schemasList, legendData, legendLoading, legendError } = useArcGis(
    activeService,
    selectedSchema,
    setExtent,
  );

  const schemaFilter = () => {
    const s = selectedSchema();
    return s ? `NOM = '${s.replace(/'/g, "''")}'` : undefined;
  };

  const toggleService = (id: string) =>
    setVisibility((prev) => ({ ...prev, [id]: !prev[id] }));

  createEffect(
    on(selectedSchema, (schema) => {
      if (schema) {
        setLoading(true);

        const fetchExtentProgram = Effect.gen(function* () {
          const arcgis = yield* ArcGisService;
          return yield* arcgis.fetchSchemaExtent(schema);
        }).pipe(
          Effect.catchAll((err) => {
            console.error(
              `Erreur réseau lors de la récupération de l'emprise`,
              err,
            );
            return Effect.succeed(null);
          }),
        );

        systemRuntime.runCallback(fetchExtentProgram, {
          onExit: (exit) => {
            if (Exit.isSuccess(exit) && exit.value) {
              setExtent({ ...exit.value });
            }
            setLoading(false);
          },
        });
      } else {
        setExtent({ ...SCHEMATIC_EXTENT });
      }
    }),
  );

  return (
    <HergeContext.Provider
      value={{
        extent,
        setExtent,
        visibility,
        toggleService,
        activeService,
        setActiveService,
        loading,
        setLoading,
        selectedSchema,
        setSelectedSchema,
        schemaFilter,
        services: SERVICES,
        schemasList,
        legendData,
        legendLoading,
        legendError,
      }}
    >
      {props.children}
    </HergeContext.Provider>
  );
};
