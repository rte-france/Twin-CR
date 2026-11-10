/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createResource, createSignal, For, Show, type Component } from "solid-js";
import { FiRefreshCw, FiSearch } from "solid-icons/fi";
import { TbMap2 } from "solid-icons/tb";
import { backendGet } from "@/services/backend";
import { openInCentral } from "@/utils/openInCentral";
import type { SynopticEntry } from "../types";

/** Lists the synoptics of the session (config.toml [input_files.argus] synoptics_dir) */
export const SynopticExplorer: Component = () => {
  const [searchQuery, setSearchQuery] = createSignal("");
  const [synoptics, { refetch }] = createResource(() =>
    backendGet<SynopticEntry[]>("/synoptics"),
  );

  const filtered = () => {
    const q = searchQuery().toLowerCase();
    return (synoptics() ?? []).filter(
      (s) => s.name.toLowerCase().includes(q) || s.title.toLowerCase().includes(q),
    );
  };

  const open = (s: SynopticEntry) => {
    openInCentral({
      id: `synoptic-${s.name}`,
      title: s.title,
      elementTag: "synoptic-viewer",
      params: { name: s.name, title: s.title },
    });
  };

  return (
    <div class="flex flex-col h-full w-full bg-sidebar-bg">
      <div class="flex items-center gap-2 p-2 border-b border-border h-9">
        <div class="relative flex-1 flex items-center">
          <FiSearch class="absolute left-2 size-3 text-[var(--fg)] opacity-50 pointer-events-none" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery()}
            onInput={(e) => setSearchQuery(e.currentTarget.value)}
            class="w-32 lg:w-40 pl-7 pr-2 py-1 text-[11px] font-mono bg-bg border border-[var(--border)] rounded transition-colors focus:outline-none focus:border-[var(--links)] text-[var(--fg)] placeholder:opacity-40"
          />
        </div>
        <button
          onClick={() => refetch()}
          class="p-1.5 rounded-md text-fg hover:bg-sidebar-active-bg hover:text-links transition-colors shrink-0"
          title="Reload the list"
        >
          <FiRefreshCw class="size-4" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-bg">
        <Show when={!synoptics.error} fallback={
          <div class="p-4 text-center text-sm text-fg opacity-50 italic">Cannot fetch the synoptics.</div>
        }>
          <Show
            when={filtered().length > 0}
            fallback={
              <div class="p-4 text-center text-sm text-fg opacity-50 italic">
                {synoptics.loading ? "Loading..." : "No synoptic found (config.toml [input_files.argus] synoptics_dir)."}
              </div>
            }
          >
            <For each={filtered()}>
              {(s) => (
                <div
                  class="group flex items-center gap-3 p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onClick={() => open(s)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") open(s);
                  }}
                >
                  <div class="text-icons group-hover:text-links transition-colors shrink-0">
                    <TbMap2 class="size-4" />
                  </div>
                  <div class="flex flex-col truncate">
                    <span class="font-medium text-sm text-fg truncate">{s.title}</span>
                    <span class="text-[10px] text-fg opacity-50">{s.name}</span>
                  </div>
                </div>
              )}
            </For>
          </Show>
        </Show>
      </div>
    </div>
  );
};
