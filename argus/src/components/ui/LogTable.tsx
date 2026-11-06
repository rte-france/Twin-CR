/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, onMount, onCleanup, Show } from "solid-js";
import {
  createGrid,
  ModuleRegistry,
  AllCommunityModule,
  type GridApi,
  type GridOptions,
  type ColDef,
} from "ag-grid-community";
import { FiArrowDown, FiChevronsDown } from "solid-icons/fi";
import type { LogService, BaseEvent } from "@/utils/createLogService";
import { agGridCustomTheme } from "@/styles/agGridCustomTheme";

ModuleRegistry.registerModules([AllCommunityModule]);

export interface LogTableProps<T extends BaseEvent> {
  service: LogService<T>;
  columnDefs: ColDef[];
  itemNameSingular?: string;
  itemNamePlural?: string;
  emptyMessage?: string;
  searchPlaceholder?: string;
}

export function LogTable<T extends BaseEvent>(props: LogTableProps<T>) {
  let gridContainerRef!: HTMLDivElement;
  const [gridApi, setGridApi] = createSignal<GridApi<any> | undefined>(
    undefined,
  );

  const [isAtBottom, setIsAtBottom] = createSignal(true);
  const [unreadCount, setUnreadCount] = createSignal(0);
  const [lastKnownCount, setLastKnownCount] = createSignal(0);
  const [searchText, setSearchText] = createSignal("");

  const itemNameS = () => props.itemNameSingular || "entry";
  const itemNameP = () => props.itemNamePlural || "entries";
  const emptyMsg = () => props.emptyMessage || "No data";
  const searchPh = () => props.searchPlaceholder || "Filter...";

  const checkIsAtBottom = () => {
    const api = gridApi();
    if (!api) return;

    const lastDisplayed = api.getLastDisplayedRowIndex();
    const totalRows = api.getDisplayedRowCount();

    if (lastDisplayed >= totalRows - 2) {
      setIsAtBottom(true);
      setUnreadCount(0);
      setLastKnownCount(props.service.events.length);
    } else {
      setIsAtBottom(false);
    }
  };

  const scrollToBottom = () => {
    const api = gridApi();
    const currentEvents = props.service.events;
    if (api && currentEvents.length > 0) {
      api.ensureIndexVisible(currentEvents.length - 1, "bottom");
      setIsAtBottom(true);
      setUnreadCount(0);
      setLastKnownCount(currentEvents.length);
    }
  };

  onMount(() => {
    props.service.loadHistory(0);
    props.service.start();

    const gridOptions: GridOptions = {
      theme: agGridCustomTheme,
      columnDefs: props.columnDefs,
      rowData: [],
      suppressCellFocus: true,
      defaultColDef: {
        resizable: true,
        sortable: false,
      },
      overlayNoRowsTemplate: `<span class="opacity-70 text-[11px] font-bold uppercase tracking-wider font-sans">${emptyMsg()}</span>`,
      onBodyScroll: checkIsAtBottom,
      getRowId: (params) => String(params.data._id),
    };

    const api = createGrid(gridContainerRef, gridOptions);
    setGridApi(api);

    onCleanup(() => {
      props.service.stop();
      if (api && !api.isDestroyed()) api.destroy();
    });
  });

  createEffect(() => {
    const api = gridApi();
    const currentEvents = props.service.events;

    if (api && !api.isDestroyed()) {
      const eventsWithIds = currentEvents.map((e, index) => ({
        ...e,
        _id: index,
      }));

      api.setGridOption("rowData", eventsWithIds);

      if (currentEvents.length === 0) {
        setIsAtBottom(true);
        setUnreadCount(0);
        setLastKnownCount(0);
      } else if (currentEvents.length > 0) {
        if (isAtBottom()) {
          setTimeout(() => {
            if (!api.isDestroyed()) {
              api.ensureIndexVisible(currentEvents.length - 1, "bottom");
              setLastKnownCount(currentEvents.length);
            }
          }, 0);
        } else {
          setUnreadCount(currentEvents.length - lastKnownCount());
        }
      }
    }
  });

  createEffect(() => {
    const api = gridApi();
    if (api && !api.isDestroyed()) {
      api.setGridOption("quickFilterText", searchText());
    }
  });

  return (
    <div class="flex flex-col h-full w-full bg-[var(--bg)] font-sans relative">
      <div class="px-4 py-2 bg-[var(--sidebar-bg)] flex items-center justify-between border-b border-[var(--border)] shrink-0 gap-4">
        <span class="text-xs font-mono text-[var(--sidebar-fg)] whitespace-nowrap">
          {props.service.events.length} {itemNameP()}
        </span>

        <div class="flex items-center gap-3 flex-1 justify-end">
          <input
            type="text"
            class="w-64 px-2.5 py-1 text-xs bg-[var(--pre-bg)] text-[var(--fg)] border border-[var(--border)] focus:border-[var(--links)] focus:outline-none rounded-sm transition-colors disabled:opacity-40"
            placeholder={searchPh()}
            value={searchText()}
            onInput={(e) => setSearchText(e.currentTarget.value)}
          />

          <div class="h-4 w-px bg-[var(--divider)] mx-1" />

          <button
            onClick={scrollToBottom}
            disabled={isAtBottom()}
            class="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider bg-[var(--links)] text-white hover:brightness-110 disabled:opacity-30 disabled:cursor-not-allowed px-2.5 py-1 rounded transition-all cursor-pointer shadow-sm"
          >
            <FiChevronsDown class="size-3" />
            To Last
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-hidden relative z-0 bg-[var(--pre-bg)]">
        <div ref={gridContainerRef} class="h-full w-full font-mono text-xs" />

        <Show when={!isAtBottom() && unreadCount() > 0}>
          <button
            onClick={scrollToBottom}
            class="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-3 py-1.5 bg-[var(--links)] text-white text-[10px] font-bold uppercase tracking-wider rounded-sm shadow-[0_4px_12px_rgba(0,0,0,0.3)] hover:brightness-110 transition-all z-10 cursor-pointer animate-in fade-in slide-in-from-bottom-2"
          >
            <FiArrowDown class="size-3" />
            {unreadCount()}{" "}
            {unreadCount() === 1 ? `new ${itemNameS()}` : `new ${itemNameP()}`}
          </button>
        </Show>
      </div>
    </div>
  );
}
