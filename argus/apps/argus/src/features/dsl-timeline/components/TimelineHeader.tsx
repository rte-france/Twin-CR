/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, createMemo } from "solid-js";
import {
  FiLayers,
  FiChevronRight,
  FiPlay,
  FiAlertCircle,
  FiSliders,
} from "solid-icons/fi";
import { useTimeline } from "../context/TimelineContext";
import { SpacingControl } from "./SpacingControl";

export function TimelineHeader() {
  const {
    statusError,
    status,
    addEvent,
    dslInput,
    setDslInput,
    leftDrawerOpen,
    setLeftDrawerOpen,
  } = useTimeline();

  const eventCount = createMemo(() => {
    const counts = status()?.event_counts;
    if (!counts) return 0;
    return counts.ready + counts.ongoing + counts.completed + counts.interrupted;
  });

  const handleSubmit = (e: Event) => {
    e.preventDefault();
    const val = dslInput().trim();
    if (val) {
      addEvent(val);
      setDslInput("");
    }
  };

  return (
    <header class="flex h-9 items-stretch justify-between bg-(--sidebar-bg) select-none z-60 shadow-sm relative">
      <div class="flex items-stretch">
        <button
          type="button"
          onClick={() => setLeftDrawerOpen(!leftDrawerOpen())}
          class="px-3 border-r border-[var(--border-light)] hover:bg-[var(--theme-hover)] transition-colors text-[var(--icons)] cursor-pointer flex items-center justify-center"
          classList={{
            "text-[var(--links)] bg-[var(--links)]/5": leftDrawerOpen(),
          }}
          title="Toggle Conditional Events"
        >
          <FiSliders class="size-4" />
        </button>

        <Show
          when={!statusError()}
          fallback={
            <div class="flex items-center gap-2 px-4 bg-[var(--warning-bg)] border-r border-[var(--warning-border)]">
              <FiAlertCircle class="size-3.5 text-[var(--warning-icon)]" />
              <span class="text-[10px] font-bold tracking-widest text-[var(--warning-icon)] uppercase">
                Offline
              </span>
            </div>
          }
        >
          <div class="flex items-center gap-2 px-3 border-r border-[var(--border-light)] min-w-[180px]">
            <FiLayers class="size-3.5 text-[var(--icons)]" />
            <span class="font-sans text-[11px] font-semibold text-[var(--fg)] leading-none truncate max-w-[120px]">
              {status()?.simulation_name || "Simulation"}
            </span>
          </div>

          <div class="flex items-center gap-4 px-4 border-r border-[var(--border-light)] bg-[var(--bg)]/40 min-w-[160px]">
            <div class="flex flex-col justify-center">
              <span class="text-[7px] uppercase tracking-[0.2em] text-[var(--icons)] font-bold mb-[3px] leading-none">
                Events
              </span>
              <span class="font-mono text-[12px] font-semibold text-[var(--fg)] leading-none">
                {eventCount().toString().padStart(2, "0")}
              </span>
            </div>
          </div>
        </Show>
      </div>

      <div class="flex-1 flex items-center px-4 max-w-2xl mx-auto">
        <form
          onSubmit={handleSubmit}
          class="w-full relative flex items-center group"
        >
          <FiChevronRight class="absolute left-2 size-3.5 text-(--icons) group-focus-within:text-(--links) transition-colors" />
          <input
            id="dsl-input-field"
            type="text"
            value={dslInput()}
            onInput={(e) => setDslInput(e.currentTarget.value)}
            placeholder="Type DSL command to enqueue... (e.g., 'at T+0:10 do action')"
            class="w-full pl-7 pr-8 py-1.5 text-[11px] font-mono bg-(--pre-bg) border border-(--border-light) rounded-[3px] text-(--code-text) outline-none focus:border-(--links) focus:ring-1 focus:ring-(--links)/30 transition-all shadow-inner placeholder:text-(--icons)/50 placeholder:font-sans"
          />
          <button
            type="submit"
            disabled={!dslInput().trim()}
            class="absolute right-1 p-1 rounded-xs text-(--icons) hover:text-(--success-color) hover:bg-(--success-color)/10 transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-(--icons)"
          >
            <FiPlay class="size-3.5" />
          </button>
        </form>
      </div>

      <div class="flex items-center px-3 border-l border-(--border-light) bg-(--bg)/20">
        <SpacingControl />
      </div>
    </header>
  );
}
