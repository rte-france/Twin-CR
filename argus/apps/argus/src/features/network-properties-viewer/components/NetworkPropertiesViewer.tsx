/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal, createEffect, createMemo,
  onMount, onCleanup, Show, type Component,
} from "solid-js";
import { ComponentTypeConfig } from "../types";
import { createGrid, type GridApi, type ColDef, type GridOptions } from "ag-grid-community";
import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";
import { DslCommand, editsToCommands } from "./dslUtils";
import { ScadaControlPopup } from "./ScadaControlPopup";
import { DslControlPopup } from "./DslControlPopup";
import { Mode } from "@/services/app-mode";
import { agGridCustomTheme } from "@/styles/agGridCustomTheme";
import { useElementData } from "../hooks/useElementData";
import { usePendingEdits } from "../hooks/usePendingEdits";

ModuleRegistry.registerModules([AllCommunityModule]);

interface NetworkPropertiesViewerProps {
  componentType: string;
  config: ComponentTypeConfig;
}

function evaluateCustomColumn(expression: string, row: Record<string, unknown>): unknown {
  try {
    const keys = Object.keys(row);
    const vals = keys.map((k) => row[k]);
    // eslint-disable-next-line no-new-func
    return new Function(...keys, `return (${expression});`)(...vals);
  } catch {
    return null;
  }
}

export const NetworkPropertiesViewer: Component<NetworkPropertiesViewerProps> = (props) => {
  let containerRef: HTMLDivElement | undefined;
  let gridApi: GridApi | undefined;
  const [showScadaPopup, setShowScadaPopup] = createSignal(false);
  const [showDslPopup, setShowDslPopup] = createSignal(false);
  const [pendingCommands, setPendingCommands] = createSignal<DslCommand[]>([]);
  const [visibleIds, setVisibleIds] = createSignal<string[]>([]);

  const applyBatchUpdate = (updates: Record<string, Record<string, number | null>>) => {
    if (!gridApi) return;
    const rows: Record<string, unknown>[] = [];
    for (const [equipmentId, fields] of Object.entries(updates)) {
      const node = gridApi.getRowNode(equipmentId);
      if (!node?.data) continue;
      rows.push({ ...node.data, ...fields });
    }
    if (rows.length > 0) gridApi.applyTransactionAsync({ update: rows });
  };

  const {
    mode, schema, allRows, isMappingLoading,
    dynamicKinds, isControllable,
  } = useElementData(
    () => props.componentType,
    applyBatchUpdate,
    undefined,
    visibleIds
  );
  const { pendingEdits, committedEdits, addEdit, commitEdit, clearEdits, hasEdits } = usePendingEdits();

  // Show AG Grid loading overlay when ressources are being loaded
  createEffect(() => {
    const loading = isMappingLoading() || schema.loading || allRows.loading;
    if (!gridApi) return;
    gridApi.setGridOption("loading", loading);
  });

  const colDefs = createMemo((): ColDef[] => {
    const s = schema();
    if (!s) return [];
    const visible = props.config.visibleColumns
      ? new Set(props.config.visibleColumns)
      : null;

    const baseCols: ColDef[] = s.columns.map((col) => ({
      field: col,
      headerName: col,
      hide: visible ? !visible.has(col) && col !== "id" : false,
      filter: true,
      sortable: true,
      resizable: true,
      editable: (params: any) => isControllable(params.data?.id, col),
      cellClass: (params: any) => {
        const hasEdit = pendingEdits().some((e) => e.rowId === params.data?.id && e.column === col);
        if (hasEdit) return "ag-cell-edited";
        if (isControllable(params.data?.id, col)) return "ag-cell-editable-custom";
        return "";
      },
    }));

    const dynamicCols: ColDef[] = dynamicKinds().map(({ kind, side, source, field }) => ({
      field,
      headerName: side ? `${kind} (${side})` : kind,
      editable: false,
      sortable: false,
      resizable: true,
      filter: false,
      cellStyle: { fontFamily: "monospace" },
      headerComponent: class {
        private el: HTMLElement = document.createElement("div");
        init() {
          this.el.className = "flex items-center gap-1.5 h-full";
          const label = document.createElement("span");
          label.innerText = side ? `${kind} (${side})` : kind;
          const badge = document.createElement("span");
          if (source === "estim") {
            badge.className = "px-1.5 py-0.5 rounded-[3px] text-[9px] font-bold uppercase tracking-wider bg-purple-500/20 text-purple-400 border border-purple-500/30";
            badge.innerText = "ESTIM";
          } else if (mode() !== Mode.Scada) {
            badge.className = "px-1.5 py-0.5 rounded-[3px] text-[9px] font-bold uppercase tracking-wider bg-green-500/20 text-green-400 border border-green-500/30";
            badge.innerText = "SIMU";
          } else {
            badge.className = "px-1.5 py-0.5 rounded-[3px] text-[9px] font-bold uppercase tracking-wider bg-blue-500/20 text-blue-400 border border-blue-500/30";
            badge.innerText = "TM/TS";
          }
          this.el.appendChild(label);
          this.el.appendChild(badge);
        }
        getGui() { return this.el; }
        destroy() {}
      },
    }));

    const customCols: ColDef[] = props.config.customColumns.map((cc) => ({
      field: `__custom__${cc.name}`,
      headerName: cc.name,
      filter: true,
      sortable: true,
      resizable: true,
    }));

    const idCol = baseCols.find((c) => c.field === "id");
    const otherBaseCols = baseCols.filter((c) => c.field !== "id");
    return [
      ...(idCol ? [idCol] : []),
      ...dynamicCols,
      ...otherBaseCols,
      ...customCols,
    ];
  });

  const rowData = createMemo(() => {
    const s = schema();
    const rows = allRows();
    if (!s || !rows) return null;

    return s.ids.map((id) => {
      const values = rows[id] ?? [];
      const row: Record<string, unknown> = {};
      s.columns.forEach((col, i) => { row[col] = values[i] ?? null; });

      // Evaluate custom columns
      for (const cc of props.config.customColumns) {
        row[`__custom__${cc.name}`] = evaluateCustomColumn(cc.expression, row);
      }
      // Placeholder for dynamic values (updated live via async transactions)
      for (const { field } of dynamicKinds()) {
        row[field] = null;
      }
      for (const edit of committedEdits()) {
        if (edit.rowId === id) row[edit.column] = edit.newValue;
      }
      for (const edit of pendingEdits()) {
        if (edit.rowId === id) row[edit.column] = edit.newValue;
      }
      return row;
    });
  });

  onMount(() => {
    if (!containerRef) return;

    const options: GridOptions = {
      theme: agGridCustomTheme,
      columnDefs: colDefs(),
      rowData: [],
      pagination: true,
      paginationPageSize: 50,
      paginationPageSizeSelector: [50, 100, 250, 500],
      defaultColDef: {
        filter: true,
        sortable: true,
        resizable: true,
        valueFormatter: (params) => {
          if (params.value === null || params.value === undefined) return "";
          if (typeof params.value === "number") return params.value.toFixed(3);
          return String(params.value);
        },
      },
      getRowId: (params) => params.data.id,
      onCellValueChanged: (event) => {
        addEdit({
          rowId: event.data.id,
          column: event.colDef.field!,
          originalValue: event.oldValue,
          newValue: event.newValue,
        });
      },
      onPaginationChanged: () => updateVisibleIds(),
      onFirstDataRendered: () => updateVisibleIds(),
      onFilterChanged: () => updateVisibleIds(),
      onSortChanged: () => updateVisibleIds(),
    };

    gridApi = createGrid(containerRef, options);
  });

  // Update col defs reactively
  createEffect(() => {
    const defs = colDefs();
    if (gridApi) gridApi.setGridOption("columnDefs", defs);
  });

  // Update row data reactively
  createEffect(() => {
    const data = rowData();
    if (!gridApi) return;
    if (!data) return;
    gridApi.setGridOption("rowData", data);
  });

  // Refresh cell styles when edits change
  createEffect(() => {
    pendingEdits();
    if (gridApi) gridApi.refreshCells({ force: true });
  });

  // Derive visible topics from current page
  const updateVisibleIds = () => {
    if (!gridApi) return;
    const currentPage = gridApi.paginationGetCurrentPage();
    const pageSize = gridApi.paginationGetPageSize();
    const start = currentPage * pageSize;
    const end = start + pageSize;
    const ids: string[] = [];
    let i = 0;
    gridApi.forEachNodeAfterFilterAndSort((node) => {
      if (i >= start && i < end && node.data?.id) ids.push(node.data.id);
      i++;
    });
    setVisibleIds(ids);
  };

  onCleanup(() => {
    gridApi?.destroy();
  });

  const dslCommands = createMemo(() => editsToCommands(pendingEdits(), props.componentType));

  const handleCommit = () => {
    if (mode() === Mode.Scada) {
      setShowScadaPopup(true);
    } else {
      setPendingCommands(dslCommands());
      setShowDslPopup(true);
    }
  };

  const handleCancel = () => {
    if (!gridApi) return;
    const revertRows: Record<string, unknown>[] = [];
    for (const edit of pendingEdits()) {
      const node = gridApi.getRowNode(edit.rowId);
      if (!node?.data) continue;
      revertRows.push({ ...node.data, [edit.column]: edit.originalValue });
    }
    if (revertRows.length > 0) gridApi.applyTransaction({ update: revertRows });
    clearEdits();
  };

  return (
    <div class="flex flex-col h-full w-full bg-[var(--bg)]">
      <Show when={hasEdits()}>
        <div class="flex items-center gap-2 px-3 py-2 border-b border-[var(--border)] bg-[var(--table-header-bg)] shrink-0">
          <span class="text-xs opacity-60">{pendingEdits().length} pending change{pendingEdits().length > 1 ? "s" : ""}</span>
          <div class="ml-auto flex gap-2">
            <button onClick={handleCancel} class="px-3 py-1.5 text-xs rounded border border-[var(--border)] hover:bg-[var(--theme-hover)] transition-colors">
              Cancel
            </button>
            <button
              onClick={() => handleCommit()}
              class="px-3 py-1.5 text-xs rounded bg-[var(--links)] text-white hover:opacity-90 transition-all"
            >
              Commit
            </button>
          </div>
        </div>
      </Show>

      <div
        ref={containerRef}
        class="flex-1 w-full"
      />

      <Show when={showScadaPopup()}>
        <ScadaControlPopup
          open={showScadaPopup()}
          onClose={() => setShowScadaPopup(false)}
          edits={pendingEdits()}
          requester="network-properties-viewer"
          onSuccess={(edits) => {
            edits.forEach((edit) => {
              commitEdit(edit.rowId, edit.column);
            });
            setShowScadaPopup(false);
          }}
        />
      </Show>

      <Show when={showDslPopup()}>
        <DslControlPopup
          open={showDslPopup()}
          onClose={() => setShowDslPopup(false)}
          commands={pendingCommands()}
          onSuccess={(ids) => {
            ids.forEach((cmdId) => {
              const cmd = pendingCommands().find((c) => c.id === cmdId);
              if (cmd) commitEdit(cmd.originalEdit.rowId, cmd.originalEdit.column);
            });
            if (!hasEdits()) setShowDslPopup(false);
          }}
        />
      </Show>
    </div>
  );
};
