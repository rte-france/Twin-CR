/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createMemo, For, Show } from "solid-js";
import { FiFileText, FiSearch } from "solid-icons/fi";
import { Tooltip } from "@kobalte/core/tooltip";
import { openInCentral } from "@/utils/openInCentral";

interface ScriptEntry {
  id: string;
  label: string;
  description: string;
}

// For now only the script loaded at initialisation by the Orchestrator is available.
const scriptEntries: ScriptEntry[] = [
  {
    id: "initial",
    label: "Initial Script",
    description: "The DSL script loaded by the Orchestrator at construction",
  },
];

export const DslExplorer = () => {
  const [searchTerm, setSearchTerm] = createSignal("");

  const filteredEntries = createMemo(() => {
    const term = searchTerm().toLowerCase().trim();
    if (!term) return scriptEntries;
    return scriptEntries.filter((entry) =>
      entry.label.toLowerCase().includes(term),
    );
  });

  const handleOpenScript = (entry: ScriptEntry) => {
    openInCentral({
      id: `dsl-${entry.id}`,
      title: entry.label,
      elementTag: "dsl-editor",
    });
  };

  return (
    <div class="flex flex-col h-full">
      <div class="p-4 space-y-4 border-b border-divider shrink-0 bg-sidebar-bg">
        <div class="relative">
          <FiSearch class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-icons" />
          <input
            type="text"
            placeholder="Search script..."
            value={searchTerm()}
            onInput={(e) => setSearchTerm(e.currentTarget.value)}
            class="w-full pl-10 pr-4 py-2 bg-search-btn-bg border border-border rounded-md text-sm focus:outline-none focus:border-sidebar-active focus:ring-1 focus:ring-sidebar-active transition-colors"
          />
        </div>

        <div class="flex items-center justify-between text-xs text-sidebar-non-existant">
          <span class="font-medium">
            {filteredEntries().length} script
            {filteredEntries().length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <Show
          when={filteredEntries().length > 0}
          fallback={
            <div class="p-4 text-sm text-icons text-center">
              No results found.
            </div>
          }
        >
          <For each={filteredEntries()}>
            {(entry) => (
              <Tooltip openDelay={400} closeDelay={100}>
                <Tooltip.Trigger
                  as="div"
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onDblClick={() => handleOpenScript(entry)}
                >
                  <div class="flex items-center gap-3 truncate group-hover:text-fg transition-colors">
                    <div class="shrink-0">
                      <FiFileText class="size-4 opacity-80" />
                    </div>
                    <span class="font-medium text-sm truncate">
                      {entry.label}
                    </span>
                  </div>
                </Tooltip.Trigger>

                <Tooltip.Portal>
                  <Tooltip.Content class="z-50 bg-sidebar-bg text-fg text-xs p-2 rounded-md shadow-lg border border-border animate-in fade-in zoom-in-95">
                    <Tooltip.Arrow class="fill-border" />
                    <span class="text-icons">{entry.description}</span>
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip>
            )}
          </For>
        </Show>
      </div>
    </div>
  );
};
