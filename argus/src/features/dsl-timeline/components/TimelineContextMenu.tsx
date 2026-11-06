/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, onCleanup, onMount } from "solid-js";
import { FiX, FiCopy, FiTerminal, FiSidebar, FiPlus } from "solid-icons/fi";
import { useTimeline } from "../context/TimelineContext";
import { fmtTime } from "../utils";

export function TimelineContextMenu() {
  const {
    contextMenu,
    setContextMenu,
    deleteEvent,
    setSelectedId,
    setDslInput,
  } = useTimeline();
  let menuRef: HTMLDivElement | undefined;

  onMount(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (menuRef && !menuRef.contains(e.target as Node)) {
        setContextMenu(null);
      }
    };
    document.addEventListener("pointerdown", handleOutsideClick, true);
    onCleanup(() =>
      document.removeEventListener("pointerdown", handleOutsideClick, true),
    );
  });

  const eventMenu = () => {
    const m = contextMenu();
    return m?.type === "event" ? m : null;
  };

  const bgMenu = () => {
    const m = contextMenu();
    return m?.type === "background" ? m : null;
  };

  return (
    <Show when={contextMenu()}>
      {(menu) => (
        <div
          ref={menuRef}
          class="absolute z-[100] min-w-[170px] bg-[var(--popover-bg)] border border-[var(--popover-border)] rounded-[4px] p-1 shadow-[var(--popover-shadow)] flex flex-col"
          style={{ top: `${menu().y}px`, left: `${menu().x}px` }}
          onContextMenu={(e) => {
            e.preventDefault();
            e.stopPropagation();
          }}
        >
          <Show when={eventMenu()}>
            {(em) => (
              <>
                <div class="px-2 py-1.5 mb-1 bg-[var(--bg)] border-b border-[var(--border-light)] rounded-t-[3px]">
                  <span class="block text-[9px] font-mono font-bold text-[var(--icons)] truncate">
                    ID: {em().event.id.substring(0, 8)}...
                  </span>
                </div>

                <button
                  type="button"
                  class="w-full px-2 py-1.5 text-left text-[11px] text-[var(--fg)] hover:bg-[var(--theme-hover)] rounded-[3px] flex items-center gap-2 transition-colors"
                  onClick={() => {
                    setSelectedId(em().event.id);
                    setContextMenu(null);
                  }}
                >
                  <FiSidebar class="size-3.5 opacity-70" /> Inspect Details
                </button>

                <button
                  type="button"
                  class="w-full px-2 py-1.5 text-left text-[11px] text-[var(--fg)] hover:bg-[var(--theme-hover)] rounded-[3px] flex items-center gap-2 transition-colors"
                  onClick={() => {
                    navigator.clipboard.writeText(em().event.action);
                    setContextMenu(null);
                  }}
                >
                  <FiTerminal class="size-3.5 opacity-70" /> Copy DSL Command
                </button>

                <button
                  type="button"
                  class="w-full px-2 py-1.5 text-left text-[11px] text-[var(--fg)] hover:bg-[var(--theme-hover)] rounded-[3px] flex items-center gap-2 transition-colors"
                  onClick={() => {
                    navigator.clipboard.writeText(em().event.id);
                    setContextMenu(null);
                  }}
                >
                  <FiCopy class="size-3.5 opacity-70" /> Copy Event ID
                </button>

                <div class="h-[1px] bg-[var(--border-light)] my-1 mx-1" />

                <button
                  type="button"
                  class="w-full px-2 py-1.5 text-left text-[11px] font-medium text-[var(--warning-icon)] hover:bg-[var(--warning-bg)] rounded-[3px] flex items-center gap-2 transition-colors"
                  onClick={() => {
                    deleteEvent(em().event.id);
                    setContextMenu(null);
                  }}
                >
                  <FiX class="size-3.5" /> Delete Event
                </button>
              </>
            )}
          </Show>

          <Show when={bgMenu()}>
            {(bg) => (
              <>
                <div class="px-2 py-1.5 mb-1 bg-[var(--bg)] border-b border-[var(--border-light)] rounded-t-[3px]">
                  <span class="block text-[9px] font-mono font-bold text-[var(--icons)] truncate">
                    Time: {fmtTime(bg().time)}
                  </span>
                </div>

                <button
                  type="button"
                  class="w-full px-2 py-1.5 text-left text-[11px] text-[var(--links)] hover:bg-[var(--sidebar-active-bg)] rounded-[3px] flex items-center gap-2 transition-colors font-medium"
                  onClick={() => {
                    setDslInput(`at ${Math.round(bg().time)} seconds, `);
                    setContextMenu(null);
                    document.getElementById("dsl-input-field")?.focus();
                  }}
                >
                  <FiPlus class="size-3.5" /> Add Event Here
                </button>
              </>
            )}
          </Show>
        </div>
      )}
    </Show>
  );
}
