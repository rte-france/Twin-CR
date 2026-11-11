/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { useTimeline } from "../context/TimelineContext";
import { FiMinus, FiPlus, FiMaximize2 } from "solid-icons/fi";

export function SpacingControl() {
  const { spacing, setSpacing } = useTimeline();

  return (
    <div class="flex items-center gap-1 bg-(--pre-bg) border border-(--border-light) rounded-[3px] p-0.5 shadow-sm">
      <button
        type="button"
        onClick={() => setSpacing(Math.max(1, spacing() - 5))}
        class="flex items-center justify-center p-1 rounded-xs text-(--icons) hover:bg-(--theme-hover) hover:text-(--fg) transition-colors"
      >
        <FiMinus class="size-3" />
      </button>

      <div class="relative flex items-center w-24 h-4 mx-1">
        <div class="absolute inset-x-0 h-0.75 bg-(--divider) rounded-full shadow-inner" />
        <input
          type="range"
          min="1"
          max="100"
          step="1"
          value={spacing()}
          onInput={(e) => setSpacing(Number(e.currentTarget.value))}
          class="absolute inset-0 w-full h-full appearance-none bg-transparent cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:size-2.5 [&::-webkit-slider-thumb]:bg-(--links) [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-[0_1px_3px_rgba(0,0,0,0.3)] hover:[&::-webkit-slider-thumb]:scale-110 [&::-webkit-slider-thumb]:transition-transform"
          title="Zoom Level (Pixels per second)"
        />
      </div>

      <button
        type="button"
        onClick={() => setSpacing(Math.min(100, spacing() + 5))}
        class="flex items-center justify-center p-1 rounded-[2px] text-(--icons) hover:bg-[var(--theme-hover)] hover:text-[var(--fg)] transition-colors"
      >
        <FiPlus class="size-3" />
      </button>

      <div class="w-[1px] h-3 bg-[var(--divider)] mx-0.5" />

      <div
        class="flex items-center gap-1 w-11 justify-center text-[var(--fg)] opacity-80"
        title="Pixels per second"
      >
        <FiMaximize2 class="size-2.5" />
        <span class="font-mono text-[9px] font-medium leading-none">
          {spacing()}
        </span>
      </div>
    </div>
  );
}
