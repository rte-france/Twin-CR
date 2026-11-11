/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { useAppMode } from "@/hooks/useAppMode";
import { useControllability } from "./useControllability";
import { createEffect, createMemo, createResource, createSignal, onCleanup, onMount } from "solid-js";
import { EstimVariable, MappingItem, MappingService } from "@/services/mapping";
import { backendGet, backendPost } from "@/services/backend";
import { DynamicKind, ElementRowsResponse, ElementSchemaResponse } from "../types";
import { Effect, Schedule } from "effect";
import { systemRuntime } from "@/config/runtime";
import { Mode } from "@/services/app-mode";
import { useDynamicValues } from "./useDynamicValues";

export function useElementData(
  getComponentType: () => string,
  applyBatchUpdate: (updates: Record<string, Record<string, number | null>>) => void,
  getElementIds?: () => string[],
  getVisibleIds?: () => string[], // optional — scopes telemetry to visible rows
) {
  const [mode] = useAppMode();
  const { checkControllability, isControllable } = useControllability();
  const [mappingItems, setMappingItems] = createSignal<MappingItem[]>([]);
  const [estimItems, setEstimItems] = createSignal<EstimVariable[]>([]);
  const [isMappingLoading, setIsMappingLoading] = createSignal(false);

  // Use mode() as dependency for all backend calls to refetch on mode change
  const [schema] = createResource(
    () => ({ type: getComponentType(), mode: mode() }),
    ({ type }) => backendGet<ElementSchemaResponse>(`/network/component-types-schema/${type}`)
  );

  const [allRows] = createResource(
    () => schema() ? { type: getComponentType(), ids: getElementIds?.() ?? schema()!.ids, mode: mode() } : null,
    async ({ type, ids }) => {
      if (ids.length === 0) return {};
      return backendPost<ElementRowsResponse>(`/network/component-types-rows/${type}`, ids);
    }
  );

  createEffect(() => {
    const s = schema();
    if (!s) return;
    const ids = getElementIds?.() ?? s.ids;
    checkControllability(ids, s.columns.filter((c) => c !== "id"));
  });

  onMount(() => {
    const program = Effect.gen(function* () {
      const mappingSvc = yield* MappingService;
      yield* Effect.repeat(
        Effect.gen(function* () {
          const state = yield* mappingSvc.getState;
          const estimState = yield* mappingSvc.getEstimState;
          const loading = state.isLoading || estimState.isLoading;
          setIsMappingLoading(loading);
          if (!loading) {
            setMappingItems(state.data);
            setEstimItems(estimState.data);
          }
        }),
        Schedule.spaced("250 millis"),  // Not a big fan of how this service must be used
      );
    });
    const cancel = systemRuntime.runCallback(program);
    onCleanup(() => cancel());
  });

  // Distinct kinds that have at least one entry matching a row in the current table
  const dynamicKinds = createMemo((): DynamicKind[] => {
    const s = schema();
    if (!s) return [];
    const rowIds = new Set(getElementIds?.() ?? s.ids);

    const mappingKinds = [...new Map(
      mappingItems()
        .filter((i) => rowIds.has(i.equipmentId))
        .map((i) => [`${i.kind}__${i.side ?? ""}`, { kind: i.kind, side: i.side ?? null }])
    ).values()].map(({ kind, side }) => ({
      kind,
      side,
      source: "mapping" as const,
      field: `__dynamic_mapping__${kind}${side ? `__${side}` : ""}`,
    }));

    const estimKinds = mode() === Mode.Scada ? [...new Map(
      estimItems()
        .filter((i) => rowIds.has(i.equipmentId))
        .map((i) => [`${i.kind}__${i.side ?? ""}`, { kind: i.kind, side: i.side ?? null }])
    ).values()].map(({ kind, side }) => ({
      kind,
      side,
      source: "estim" as const,
      field: `__dynamic_estim__${kind}${side ? `__${side}` : ""}`,
    })) : [];

    return [...mappingKinds, ...estimKinds].sort((a, b) => a.kind.localeCompare(b.kind) || (a.side ?? "").localeCompare(b.side ?? ""));
  });

  // Live updates
  const { start, stop } = useDynamicValues(
    mappingItems,
    () => new Set(getVisibleIds?.() ?? getElementIds?.() ?? schema()?.ids ?? []),
    applyBatchUpdate,
  );

  createEffect(() => {
    const s = schema();
    if (!s) return [];
    const kinds = dynamicKinds();
    if (kinds.length === 0) return stop;

    const ids = new Set(getVisibleIds ? getVisibleIds() : (getElementIds?.() ?? s.ids));
    const mapping = mappingItems();
    const estim = estimItems();
    if (mapping.length === 0 && estim.length === 0) return;

    const topics = [...new Set(
      mappingItems().filter((i) => ids.has(i.equipmentId)).map((i) => i.topic)
    )];
    const estimTopics = [...new Set(
      estimItems().filter((i) => ids.has(i.equipmentId)).map((i) => i.topic)
    )];
    start(topics, estimTopics, mode());
    return stop;
  });

  return {
    mode, schema, allRows, isMappingLoading,
    dynamicKinds,
    isControllable,
  };
}
