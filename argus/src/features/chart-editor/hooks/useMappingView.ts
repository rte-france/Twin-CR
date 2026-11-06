/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createMemo, onMount, onCleanup } from "solid-js";
import { Effect, Schedule } from "effect";
import { systemRuntime } from "@/config/runtime";
import {
  EstimState,
  MappingService,
  type MappingState,
} from "@/services/mapping";

export const useMappingView = () => {
  const [mappingState, setMappingState] = createSignal<MappingState>({
    data: [],
    isLoading: false,
    error: null,
    activeMode: null,
  });

  const [estimState, setEstimState] = createSignal<EstimState>({
    data: [],
    isLoading: false,
    error: null,
    activeMode: null,
  });

  const [searchQuery, setSearchQuery] = createSignal("");
  const [currentPage, setCurrentPage] = createSignal(1);
  const [pageSize, setPageSize] = createSignal(50);

  onMount(() => {
    const program = Effect.gen(function* () {
      const mappingSvc = yield* MappingService;

      yield* Effect.repeat(
        Effect.gen(function* () {
          const state = yield* mappingSvc.getState;
          setMappingState((prev) => {
            if (
              prev.data === state.data &&
              prev.isLoading === state.isLoading &&
              prev.error === state.error
            ) {
              return prev;
            }
            return { ...state, data: [...state.data] };
          });

          const eState = yield* mappingSvc.getEstimState;
          setEstimState((prev) => {
            if (
              prev.data === eState.data &&
              prev.isLoading === eState.isLoading &&
              prev.error === eState.error
            )
              return prev;
            return { ...eState, data: [...eState.data] };
          });
        }),
        Schedule.spaced("250 millis"),
      );
    });

    const cancel = systemRuntime.runCallback(program);
    onCleanup(() => cancel());
  });

  const filteredData = createMemo(() => {
    const query = searchQuery().toLowerCase().trim();
    const allData = mappingState().data;

    if (!query) return allData;

    return allData.filter((item) => {
      if (!item) return false;

      return (
        (item.equipmentId?.toLowerCase() ?? "").includes(query) ||
        (item.substation?.toLowerCase() ?? "").includes(query)
      );
    });
  });

  const totalItems = createMemo(() => filteredData().length);
  const totalPages = createMemo(
    () => Math.ceil(totalItems() / pageSize()) || 1,
  );

  const paginatedData = createMemo(() => {
    const items = filteredData();
    const start = (currentPage() - 1) * pageSize();
    const end = start + pageSize();
    return items.slice(start, end);
  });

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setCurrentPage(1);
  };

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages()) {
      setCurrentPage(page);
    }
  };

  return {
    refresh: (force?: boolean) => {
      systemRuntime.runPromise(
        Effect.gen(function* () {
          const svc = yield* MappingService;
          yield* svc.fetch(force);
        }),
      );
    },
    isLoading: () => mappingState().isLoading,
    error: () => mappingState().error,
    rawData: () => mappingState().data,

    isEstimLoading: () => estimState().isLoading,
    estimError: () => estimState().error,
    rawEstimData: () => estimState().data,

    items: paginatedData,
    searchQuery,
    setSearchQuery: handleSearch,
    currentPage,
    totalPages,
    totalItems,
    pageSize,
    setPageSize,
    goToPage,
  };
};
