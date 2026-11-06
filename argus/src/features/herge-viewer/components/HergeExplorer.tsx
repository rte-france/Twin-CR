/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createMemo,
  onMount,
  onCleanup,
  For,
  Show,
} from "solid-js";
import { FiMap, FiSearch } from "solid-icons/fi";
import { FaSolidSpinner } from "solid-icons/fa";
import { Effect, Exit } from "effect";
import { openInCentral } from "@/utils/openInCentral";
import { ArcGisService } from "../services/arcgis";
import { systemRuntime } from "@/config/runtime";

export const HergeExplorer = () => {
  const [zones, setZones] = createSignal<readonly string[]>([]);
  const [isLoading, setIsLoading] = createSignal(true);
  const [searchTerm, setSearchTerm] = createSignal("");

  const filteredZones = createMemo(() => {
    const term = searchTerm().toLowerCase().trim();
    if (!term) return zones();
    return zones().filter((zoneName) => zoneName.toLowerCase().includes(term));
  });

  onMount(() => {
    const program = Effect.gen(function* () {
      const arcgis = yield* ArcGisService;
      return yield* arcgis.fetchSchemasList;
    }).pipe(
      Effect.catchAll((err) => {
        console.error("Failed to fetch Hergé zones", err);
        return Effect.succeed([]);
      }),
    );

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        setIsLoading(false);
        if (Exit.isSuccess(exit)) {
          setZones(exit.value);
        }
      },
    });

    onCleanup(() => cancel());
  });

  const handleOpenZone = (schemaName: string) => {
    openInCentral({
      id: `herge-${schemaName}`,
      title: schemaName,
      elementTag: "herge-viewer",
      params: {
        selectedSchema: schemaName,
      },
    });
  };

  return (
    <div class="flex flex-col h-full">
      <div class="p-4 space-y-4 border-b border-divider shrink-0 bg-sidebar-bg">
        <div class="relative">
          <FiSearch class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-icons" />
          <input
            type="text"
            placeholder="Search zone..."
            value={searchTerm()}
            onInput={(e) => setSearchTerm(e.currentTarget.value)}
            disabled={isLoading()}
            class="w-full pl-10 pr-4 py-2 bg-search-btn-bg border border-border rounded-md text-sm focus:outline-none focus:border-sidebar-active focus:ring-1 focus:ring-sidebar-active disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          />
        </div>

        <div class="flex items-center justify-between text-xs text-sidebar-non-existant">
          <span class="font-medium">
            {filteredZones().length} zone
            {filteredZones().length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <Show
          when={!isLoading()}
          fallback={
            <div class="flex items-center justify-center p-4 text-icons opacity-70">
              <FaSolidSpinner class="animate-spin size-5" />
            </div>
          }
        >
          <Show
            when={filteredZones().length > 0}
            fallback={
              <div class="p-4 text-sm text-icons text-center">
                {zones().length === 0
                  ? "No zones available."
                  : "No results found."}
              </div>
            }
          >
            <For each={filteredZones()}>
              {(zoneName) => (
                <div
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onDblClick={() => handleOpenZone(zoneName)}
                >
                  <div class="flex items-center gap-3 truncate group-hover:text-fg transition-colors">
                    <div class="shrink-0">
                      <FiMap class="size-4 opacity-80" />
                    </div>
                    <span class="font-medium text-sm truncate">{zoneName}</span>
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
