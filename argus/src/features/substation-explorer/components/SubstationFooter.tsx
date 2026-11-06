/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { FiChevronLeft, FiChevronRight } from "solid-icons/fi";
import { useSubstationExplorerContext } from "../providers/SubstationExplorerProvider";

export const SubstationFooter = () => {
  const { setCurrentPage, currentPage, totalPages } =
    useSubstationExplorerContext();

  return (
    <div class="p-4 border-t border-divider bg-sidebar-bg flex items-center justify-between gap-4 h-10">
      <div class="flex items-center gap-2 text-sm">
        <span class="text-sidebar-non-existant">Page</span>
        <input
          type="number"
          value={currentPage()}
          onInput={(e) => {
            const val = Math.max(
              1,
              Math.min(totalPages(), Number(e.currentTarget.value)),
            );
            setCurrentPage(val);
          }}
          class="w-10 text-center bg-bg border border-border rounded py-1 text-sm outline-none focus:border-sidebar-active [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
        <span class="text-sidebar-non-existant italic">/ {totalPages()}</span>
      </div>

      <div class="flex gap-2">
        <button
          disabled={currentPage() === 1}
          onClick={() => setCurrentPage((p) => p - 1)}
          class="p-2 rounded border border-border disabled:opacity-20 enabled:hover:bg-footer-btn-bg-hover transition-colors"
        >
          <FiChevronLeft class="size-4" />
        </button>
        <button
          disabled={currentPage() >= totalPages()}
          onClick={() => setCurrentPage((p) => p + 1)}
          class="p-2 rounded border border-border disabled:opacity-20 enabled:hover:bg-footer-btn-bg-hover transition-colors"
        >
          <FiChevronRight class="size-4" />
        </button>
      </div>
    </div>
  );
};
