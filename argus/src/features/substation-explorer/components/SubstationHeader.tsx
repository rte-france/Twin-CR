/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { FiSearch } from "solid-icons/fi";
import { useSubstationExplorerContext } from "../providers/SubstationExplorerProvider";

export const SubstationHeader = () => {
  const {
    searchTerm,
    setSearchTerm,
    setCurrentPage,
    totalCount,
    toggleAll,
    expanded,
  } = useSubstationExplorerContext();

  return (
    <div class="p-4 space-y-4 border-b border-divider bg-sidebar-bg">
      <div class="relative">
        <FiSearch class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-icons" />
        <input
          type="text"
          placeholder="Search Substation"
          value={searchTerm()}
          onInput={(e) => {
            setSearchTerm(e.currentTarget.value);
            setCurrentPage(1);
          }}
          class="w-full pl-10 pr-4 py-2 bg-search-btn-bg border border-border rounded-md text-sm focus:outline-none focus:border-sidebar-active focus:ring-1 focus:ring-sidebar-active"
        />
      </div>

      <div class="flex items-center justify-between text-xs text-sidebar-non-existant">
        <span class="font-medium">
          {totalCount()} substation{totalCount() > 1 ? "s" : ""}
        </span>
        <button
          onClick={toggleAll}
          class="text-links hover:text-sidebar-active font-semibold transition-colors"
        >
          {expanded().size > 0 ? "Fold All" : "Unfold All"}
        </button>
      </div>
    </div>
  );
};
