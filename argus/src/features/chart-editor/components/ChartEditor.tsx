/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createEffect,
  onMount,
  onCleanup,
  Show,
  type Component,
  createMemo,
} from "solid-js";
import {
  createGrid,
  ModuleRegistry,
  AllCommunityModule,
  type GridApi,
  type GridOptions,
  type ColDef,
} from "ag-grid-community";
import { Effect } from "effect";
import { systemRuntime } from "@/config/runtime";
import {
  FiPlus,
  FiMinus,
  FiTrash2,
  FiFilter,
  FiDatabase,
  FiActivity,
} from "solid-icons/fi";

import { useMappingView } from "../hooks/useMappingView";
import { ChartDataRow, ChartService } from "@/services/chart";
import { useAppMode } from "@/hooks/useAppMode";
import { agGridCustomTheme } from "@/styles/agGridCustomTheme";
import { ChartEditorProps } from "../types";

ModuleRegistry.registerModules([AllCommunityModule]);

type ViewMode = "all" | "in-chart";
type DataSource = "mapping" | "estim";

function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number,
): T {
  let timeoutId: ReturnType<typeof setTimeout>;
  return function (this: any, ...args: Parameters<T>) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), wait);
  } as T;
}

const getItemKey = (item: any, forceEstim?: boolean) => {
  const eqId = item.equipmentId || "";
  const isEstim = forceEstim !== undefined ? forceEstim : !!item.isEstim;
  const type = isEstim ? "estim" : "tmts";
  return item.id
    ? `${item.id}-${type}`
    : `${eqId}-${item.kind}-${item.side || ""}-${type}`;
};

export const ChartEditor: Component<ChartEditorProps> = (props) => {
  let gridContainerRef!: HTMLDivElement;

  const [mode] = useAppMode();
  const dId = () => props.dashboardId || "default";
  const mapping = useMappingView();

  const [savedSelection, setSavedSelection] = createSignal<ChartDataRow[]>([]);
  const [gridApi, setGridApi] = createSignal<GridApi<any> | undefined>(
    undefined,
  );
  const [selectedCount, setSelectedCount] = createSignal(0);
  const [viewMode, setViewMode] = createSignal<ViewMode>("all");
  const [dataSource, setDataSource] = createSignal<DataSource>("mapping");

  const [currentPage, setCurrentPage] = createSignal(1);
  const [totalPages, setTotalPages] = createSignal(1);
  const [totalItems, setTotalItems] = createSignal(0);
  const [pageSize, setPageSize] = createSignal(50);

  const handleSearchInput = debounce((value: string) => {
    mapping.setSearchQuery(value);
  }, 300);

  const loadSelection = () => {
    systemRuntime
      .runPromise(
        Effect.gen(function* () {
          const chartSvc = yield* ChartService;
          return yield* chartSvc.getSelection(dId());
        }),
      )
      .then(setSavedSelection);
  };

  const handleSelectionEvent = () => loadSelection();

  onMount(() => {
    if (props.initialQuery) {
      mapping.setSearchQuery(props.initialQuery);
    }

    loadSelection();
    window.addEventListener("chart-selection-added", handleSelectionEvent);
    window.addEventListener("chart-selection-cleared", handleSelectionEvent);

    const gridOptions: GridOptions = {
      theme: agGridCustomTheme,
      columnDefs: columnDefs(),
      rowData: [],
      rowSelection: "multiple",
      suppressRowClickSelection: true,
      getRowId: (params) => {
        const isEstimView =
          viewMode() === "in-chart"
            ? !!params.data.isEstim
            : dataSource() === "estim";
        return getItemKey(params.data, isEstimView);
      },
      pagination: true,
      paginationPageSize: 50,
      suppressPaginationPanel: true,

      onPaginationChanged: (event) => {
        if (event.api) {
          setCurrentPage(event.api.paginationGetCurrentPage() + 1);
          setTotalPages(event.api.paginationGetTotalPages() || 1);
        }
      },
      onModelUpdated: (event) => {
        if (event.api) {
          setTotalItems(event.api.getDisplayedRowCount());
          setTotalPages(event.api.paginationGetTotalPages() || 1);
        }
      },

      defaultColDef: {
        flex: 1,
        minWidth: 90,
        resizable: true,
        sortable: true,
      },

      getRowClass: (params) => {
        if (!params.data) return "";
        const isEstimView =
          viewMode() === "in-chart"
            ? !!params.data.isEstim
            : dataSource() === "estim";
        const currentId = getItemKey(params.data, isEstimView);
        const isInChart = savedSelection().some(
          (s) => getItemKey(s) === currentId,
        );
        return isInChart
          ? "!bg-[var(--sidebar-active-bg)] border-l-2 border-l-[var(--links)]"
          : "";
      },

      overlayNoRowsTemplate:
        '<span class="opacity-70 text-[11px] font-bold uppercase tracking-wider">No data found</span>',
      overlayLoadingTemplate:
        '<span class="opacity-70 text-[11px] font-bold uppercase tracking-wider">Loading system data...</span>',

      onSelectionChanged: (event) => {
        setSelectedCount(event.api.getSelectedNodes().length);
      },
    };

    const api = createGrid(gridContainerRef, gridOptions);
    setGridApi(api);

    onCleanup(() => {
      window.removeEventListener("chart-selection-added", handleSelectionEvent);
      window.removeEventListener(
        "chart-selection-cleared",
        handleSelectionEvent,
      );
      if (api && !api.isDestroyed()) api.destroy();
    });
  });

  // Définition de colonnes unifiée pour les deux modes
  const columnDefs = createMemo<ColDef[]>(() => {
    return [
      {
        headerName: "Equipment ID",
        headerCheckboxSelection: true,
        checkboxSelection: true,
        minWidth: 150,
        valueGetter: (params) => {
          if (!params.data) return "";
          return (
            params.data.equipmentId ||
            params.data.id  // Fallback for elements without equipmentId
          );
        },
      },
      {
        headerName: "Source",
        field: "isEstim",
        maxWidth: 90,
        cellRenderer: (params: any) => {
          if (!params.data) return "";
          const isE =
            viewMode() === "in-chart"
              ? !!params.data.isEstim
              : dataSource() === "estim";
          const el = document.createElement("span");

          if (isE) {
            el.className =
              "px-1.5 py-0.5 rounded-[3px] text-[9px] font-bold uppercase tracking-wider bg-purple-500/20 text-purple-400 border border-purple-500/30";
            el.innerText = "ESTIM";
          } else if (mode() === "GameMaster") {
            el.className =
              "px-1.5 py-0.5 rounded-[3px] text-[9px] font-bold uppercase tracking-wider bg-green-500/20 text-green-400 border border-green-500/30";
            el.innerText = "SIMU";
          } else {
            el.className =
              "px-1.5 py-0.5 rounded-[3px] text-[9px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-400 border border-blue-500/30";
            el.innerText = "TM/TS";
          }

          return el;
        },
      },
      {
        field: "kind",
        headerName: "Kind",
        filter: true,
        maxWidth: 100,
        filterParams: {
          filterOptions: ["equals", "notEqual"],
          maxNumConditions: 1,
          buttons: ["reset"],
        },
      },
      {
        field: "side",
        headerName: "Side",
        filter: true,
        maxWidth: 100,
      },
      {
        field: "substation",
        headerName: "Substation",
        filter: true,
        flex: 1,
      },
    ];
  });

  createEffect(() => {
    const api = gridApi();
    const defs = columnDefs();

    if (api && !api.isDestroyed()) {
      api.setGridOption("columnDefs", defs);
    }
  });

  createEffect(() => {
    const api = gridApi();
    if (!api || api.isDestroyed()) return;

    const isFocusMode = viewMode() === "in-chart";
    const isEstim = dataSource() === "estim";

    const loading = isEstim ? mapping.isEstimLoading() : mapping.isLoading();

    let data = [];
    if (isFocusMode) {
      data = savedSelection();
    } else {
      data = isEstim
        ? (mapping.rawEstimData?.() ?? [])
        : (mapping.rawData?.() ?? []);
    }

    api.setGridOption("loading", !isFocusMode && loading);

    if (!loading || isFocusMode) {
      api.setGridOption("rowData", data);
    }
  });

  createEffect(() => {
    const api = gridApi();
    if (api && !api.isDestroyed()) {
      api.setGridOption("quickFilterText", mapping.searchQuery());
    }
  });

  createEffect(() => {
    const api = gridApi();
    if (
      api &&
      !api.isDestroyed() &&
      !mapping.isLoading() &&
      !mapping.isEstimLoading() &&
      viewMode() === "all"
    ) {
      api.redrawRows();
    }
  });

  const addSelectedToChart = () => {
    const api = gridApi();
    if (!api) return;

    const selectedNodes = api.getSelectedNodes();
    const newData: any[] = selectedNodes
      .map((node) => {
        if (!node.data) return null;
        return {
          ...node.data,
          isEstim:
            viewMode() === "in-chart"
              ? node.data.isEstim
              : dataSource() === "estim",
        };
      })
      .filter(Boolean);

    if (newData.length === 0) return;

    systemRuntime
      .runPromise(
        Effect.gen(function* () {
          const chartSvc = yield* ChartService;
          const existingData = yield* chartSvc.getSelection(dId());
          const merged = [...existingData, ...newData];
          const unique = Array.from(
            new Map(merged.map((item) => [getItemKey(item), item])).values(),
          );
          yield* chartSvc.setSelection(dId(), unique);
        }),
      )
      .then(() => {
        window.dispatchEvent(
          new CustomEvent("chart-selection-added", {
            detail: { chartId: dId(), addedItems: newData },
          }),
        );
        api.deselectAll();
      });
  };

  const removeSelectedFromChart = () => {
    const api = gridApi();
    if (!api) return;

    const selectedNodes = api.getSelectedNodes();
    const idsToRemove = new Set(
      selectedNodes
        .map((node) => {
          if (!node.data) return null;
          const isEstimView =
            viewMode() === "in-chart"
              ? !!node.data.isEstim
              : dataSource() === "estim";
          return getItemKey(node.data, isEstimView);
        })
        .filter(Boolean),
    );

    if (idsToRemove.size === 0) return;

    systemRuntime
      .runPromise(
        Effect.gen(function* () {
          const chartSvc = yield* ChartService;
          const existingData = yield* chartSvc.getSelection(dId());
          const filtered = existingData.filter(
            (item) => !idsToRemove.has(getItemKey(item)),
          );
          yield* chartSvc.setSelection(dId(), filtered);
        }),
      )
      .then(() => {
        window.dispatchEvent(
          new CustomEvent("chart-selection-cleared", {
            detail: { chartId: dId() },
          }),
        );
        api.deselectAll();
      });
  };

  const clearEntireChart = () => {
    systemRuntime
      .runPromise(
        Effect.gen(function* () {
          const chartSvc = yield* ChartService;
          yield* chartSvc.clearSelection(dId());
        }),
      )
      .then(() => {
        window.dispatchEvent(
          new CustomEvent("chart-selection-cleared", {
            detail: { chartId: dId() },
          }),
        );
        gridApi()?.deselectAll();
      });
  };

  const handlePageSizeChange = (e: Event) => {
    const newSize = parseInt((e.target as HTMLSelectElement).value, 10);
    setPageSize(newSize);
    gridApi()?.setGridOption("paginationPageSize", newSize);
  };

  const goToPage = (page: number) => {
    gridApi()?.paginationGoToPage(page - 1);
  };

  return (
    <div class="flex flex-col w-full h-full bg-[var(--bg)] font-mono">
      <div class="flex flex-col gap-2 p-3 bg-[var(--sidebar-bg)] border-b border-[var(--divider)] shrink-0">
        <div class="flex items-center gap-2">
          <div class="flex bg-[var(--pre-bg)] border border-[var(--border)] rounded-sm p-0.5 shrink-0 shadow-sm">
            <button
              class={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] uppercase tracking-wider font-bold rounded-sm transition-colors ${
                viewMode() === "all" && dataSource() === "mapping"
                  ? "bg-[var(--sidebar-active-bg)] text-[var(--links)]"
                  : "text-[var(--fg)] opacity-60 hover:opacity-100"
              }`}
              onClick={() => {
                setViewMode("all");
                setDataSource("mapping");
              }}
            >
              <FiDatabase class="size-3" />{" "}
              {mode() === "GameMaster" ? "Simu" : "TM/TS"}
            </button>

            <button
              class={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] uppercase tracking-wider font-bold rounded-sm transition-colors ${
                viewMode() === "all" && dataSource() === "estim"
                  ? "bg-[var(--sidebar-active-bg)] text-[var(--links)]"
                  : "text-[var(--fg)] opacity-60 hover:opacity-100"
              }`}
              onClick={() => {
                setViewMode("all");
                setDataSource("estim");
              }}
            >
              <FiActivity class="size-3" /> Estim
            </button>

            <button
              class={`flex items-center gap-1.5 px-2.5 py-1 text-[11px] uppercase tracking-wider font-bold rounded-sm transition-colors ${
                viewMode() === "in-chart"
                  ? "bg-[var(--sidebar-active-bg)] text-[var(--links)]"
                  : "text-[var(--fg)] opacity-60 hover:opacity-100"
              }`}
              onClick={() => setViewMode("in-chart")}
            >
              <FiFilter class="size-3" /> Focus [{savedSelection().length}]
            </button>
          </div>

          <input
            type="text"
            class="flex-1 px-2.5 py-1 text-xs bg-[var(--pre-bg)] text-[var(--fg)] border border-[var(--border)] focus:border-[var(--links)] focus:outline-none rounded-sm transition-colors shadow-sm disabled:opacity-40"
            placeholder="Search equipment, ID, substation..."
            onInput={(e) => handleSearchInput(e.currentTarget.value)}
            disabled={viewMode() === "in-chart"}
          />
        </div>

        <div class="flex items-center justify-between mt-1">
          <div class="flex gap-1.5">
            <button
              onClick={addSelectedToChart}
              disabled={selectedCount() === 0 || viewMode() === "in-chart"}
              class="flex items-center gap-1 px-2.5 py-1 rounded-sm bg-[var(--links)] text-white hover:brightness-110 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-[11px] font-bold uppercase tracking-wider shadow-sm"
            >
              <FiPlus class="size-3" /> Add
            </button>
            <button
              onClick={removeSelectedFromChart}
              disabled={selectedCount() === 0}
              class="flex items-center gap-1 px-2.5 py-1 rounded-sm border border-[var(--warning-border)] text-[var(--warning-icon)] hover:bg-[var(--warning-bg)] disabled:opacity-30 disabled:border-[var(--border)] disabled:text-[var(--fg)] disabled:cursor-not-allowed transition-all text-[11px] font-bold uppercase tracking-wider"
            >
              <FiMinus class="size-3" /> Remove
            </button>
          </div>

          <button
            onClick={clearEntireChart}
            disabled={savedSelection().length === 0}
            class="flex items-center gap-1 text-[var(--warning-icon)] hover:brightness-125 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] px-2 py-1 font-bold uppercase tracking-wider transition-colors"
          >
            <FiTrash2 class="size-3" /> Clear
          </button>
        </div>
      </div>

      <div class="flex flex-col flex-1 overflow-hidden relative z-0 bg-[var(--bg)]">
        <Show
          when={
            mapping.error() &&
            viewMode() === "all" &&
            dataSource() === "mapping"
          }
        >
          <div class="px-3 py-1 bg-red-500/10 text-red-500 border-b border-red-500/20 text-[10px] uppercase font-bold tracking-wider">
            ERR: {mapping.error()?.message}
          </div>
        </Show>
        <Show
          when={
            mapping.estimError() &&
            viewMode() === "all" &&
            dataSource() === "estim"
          }
        >
          <div class="px-3 py-1 bg-red-500/10 text-red-500 border-b border-red-500/20 text-[10px] uppercase font-bold tracking-wider">
            ERR: {mapping.estimError()?.message}
          </div>
        </Show>

        <div ref={gridContainerRef} class="flex-1 w-full" />
      </div>

      <Show when={viewMode() === "all"}>
        <div class="flex items-center justify-between px-3 py-1.5 bg-[var(--sidebar-bg)] border-t border-[var(--border)] shrink-0">
          <div class="flex items-center gap-2 text-[11px] text-[var(--fg)] opacity-80 uppercase tracking-wider">
            <span>Show</span>
            <select
              class="bg-[var(--pre-bg)] border border-[var(--border)] rounded-sm px-1 py-0.5 text-[var(--fg)] focus:outline-none focus:border-[var(--links)] shadow-sm"
              value={pageSize()}
              onChange={handlePageSizeChange}
              disabled={
                dataSource() === "estim"
                  ? mapping.isEstimLoading()
                  : mapping.isLoading()
              }
            >
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="500">500</option>
            </select>
            <span class="font-bold">/ {totalItems()}</span>
          </div>

          <div class="flex items-center gap-3">
            <div class="flex items-center gap-1.5 text-[11px] text-[var(--fg)] opacity-80 uppercase tracking-wider">
              <span>PG</span>
              <input
                type="number"
                class="no-spinners w-8 text-center bg-[var(--pre-bg)] border border-[var(--border)] rounded-sm px-1 py-0.5 text-[var(--fg)] focus:outline-none focus:border-[var(--links)] font-bold shadow-sm"
                value={currentPage()}
                min="1"
                max={totalPages()}
                onChange={(e) => goToPage(parseInt(e.currentTarget.value, 10))}
                disabled={
                  (dataSource() === "estim"
                    ? mapping.isEstimLoading()
                    : mapping.isLoading()) || totalPages() === 0
                }
              />
              <span>/ {totalPages()}</span>
            </div>

            <div class="flex gap-1">
              <button
                onClick={() => goToPage(currentPage() - 1)}
                disabled={
                  currentPage() === 1 ||
                  (dataSource() === "estim"
                    ? mapping.isEstimLoading()
                    : mapping.isLoading()) ||
                  totalPages() === 0
                }
                class="px-2 py-0.5 rounded-sm bg-[var(--footer-btn-bg)] border border-[var(--border)] text-[var(--fg)] hover:bg-[var(--theme-hover)] disabled:opacity-30 transition-all text-[11px] uppercase font-bold shadow-sm"
              >
                &lt;
              </button>
              <button
                onClick={() => goToPage(currentPage() + 1)}
                disabled={
                  currentPage() === totalPages() ||
                  (dataSource() === "estim"
                    ? mapping.isEstimLoading()
                    : mapping.isLoading()) ||
                  totalPages() === 0
                }
                class="px-2 py-0.5 rounded-sm bg-[var(--footer-btn-bg)] border border-[var(--border)] text-[var(--fg)] hover:bg-[var(--theme-hover)] disabled:opacity-30 transition-all text-[11px] uppercase font-bold shadow-sm"
              >
                &gt;
              </button>
            </div>
          </div>
        </div>
      </Show>
    </div>
  );
};
