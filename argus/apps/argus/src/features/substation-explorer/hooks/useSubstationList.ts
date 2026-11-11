/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Console } from "effect";
import { createSignal, onMount, createMemo, createEffect } from "solid-js";
import type { Substation } from "../types";
import { backendGet } from "@/services/backend";

const SEARCH_STORAGE_KEY = "substation_search_term";

export const useSubstationList = () => {
  const [substations, setSubstations] = createSignal<readonly Substation[]>([]);

  const [searchTerm, setSearchTerm] = createSignal(
    localStorage.getItem(SEARCH_STORAGE_KEY) || "",
  );

  const [currentPage, setCurrentPage] = createSignal(1);
  const pageSize = 15;

  createEffect(() => {
    const currentSearch = searchTerm();
    localStorage.setItem(SEARCH_STORAGE_KEY, currentSearch);

    setCurrentPage(1);
  });

  onMount(async () => {
    try {
      const rawData = await backendGet<any[]>("/substation-list");
      setSubstations(rawData.map((s) => ({
        id: s.substation_id,
        tso: s.tso || "",
        voltageLevels: (s.voltageLevels || []).map((vl: any) => ({
          id: vl.vl_id,
          nominal_v: vl.nominalVoltage,
        })),
      })));
    } catch (e) {
      Console.error("Failed to fetch substations", e);
    }
  });

  const filteredData = createMemo(() => {
    const term = searchTerm().toLowerCase();
    const list = substations();
    if (!term) return list;

    return list.filter((s) => {
      const nameMatch = s.id?.toLowerCase().includes(term);
      const vlMatch = s.voltageLevels?.some(
        (v) =>
          v.id?.toLowerCase().includes(term) ||
          v.nominal_v?.toString().includes(term),
      );
      return nameMatch || vlMatch;
    });
  });

  const paginatedData = createMemo(() => {
    const start = (currentPage() - 1) * pageSize;
    return filteredData().slice(start, start + pageSize);
  });

  const totalPages = createMemo(
    () => Math.ceil(filteredData().length / pageSize) || 1,
  );

  return {
    substations: paginatedData,
    totalCount: () => filteredData().length,
    searchTerm,
    setSearchTerm,
    currentPage,
    setCurrentPage,
    totalPages,
  };
};
