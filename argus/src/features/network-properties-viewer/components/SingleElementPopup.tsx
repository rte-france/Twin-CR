/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createMemo, Show, type Component, createEffect, onCleanup, onMount } from "solid-js";
import { Mode } from "@/services/app-mode";
import { ScadaControlPopup } from "./ScadaControlPopup";
import { DslControlPopup } from "./DslControlPopup";
import { DslCommand, editsToCommands } from "./dslUtils";
import { useElementData } from "../hooks/useElementData";
import { AllCommunityModule, ColDef, createGrid, GridApi, GridOptions, ModuleRegistry } from "ag-grid-community";
import { agGridCustomTheme } from "@/styles/agGridCustomTheme";
import { Dialog } from "@kobalte/core/dialog";
import { FiX } from "solid-icons/fi";
import { usePendingEdits } from "../hooks/usePendingEdits";

ModuleRegistry.registerModules([AllCommunityModule]);

interface SingleElementPopupProps {
  open: boolean;
  onClose: () => void;
  componentType: string;
  elementId: string;
}

export const SingleElementPopup: Component<SingleElementPopupProps> = (props) => {
  let containerRef: HTMLDivElement | undefined;
  let gridApi: GridApi | undefined;

  const [showScadaPopup, setShowScadaPopup] = createSignal(false);
  const [showDslPopup, setShowDslPopup] = createSignal(false);
  const [pendingCommands, setPendingCommands] = createSignal<DslCommand[]>([]);

  const applyBatchUpdate = (updates: Record<string, Record<string, number | null>>) => {
    const vals = updates[props.elementId];
    if (!vals || !gridApi) return;
    const rowUpdates = Object.entries(vals).map(([field, value]) => {
      const node = gridApi!.getRowNode(field);
      return { ...node?.data, field, value };
    });
    if (rowUpdates.length > 0) gridApi.applyTransactionAsync({ update: rowUpdates });
  };

  const {
    mode, schema, allRows, isMappingLoading,
    dynamicKinds, isControllable,
  } = useElementData(
    () => props.componentType,
    applyBatchUpdate,
    () => [props.elementId],
  );
  const { pendingEdits, committedEdits, addEdit, commitEdit, clearEdits, hasEdits } = usePendingEdits();

  // Show AG Grid loading overlay when ressources are being loaded
  createEffect(() => {
    const loading = isMappingLoading() || schema.loading || allRows.loading;
    if (!gridApi) return;
    gridApi.setGridOption("loading", loading);
  });

  const rows = createMemo(() => {
    const s = schema();
    const data = allRows()?.[props.elementId];
    if (!s || !data) return [];

    const baseRows = s.columns
      .map((col, i) => ({ col, value: data[i] }))
      .filter(({ col }) => col !== "id")
      .map(({ col, value }) => {
        const pending = pendingEdits().find((e) => e.column === col);
        const committedVal = committedEdits().find((e) => e.column === col);
        return {
          field: col,
          label: col,
          value: pending ? pending.newValue : committedVal ? committedVal.newValue : value,
          originalValue: committedVal ? committedVal.newValue : value,
          isEdited: !!pending,
          isControllable: isControllable(props.elementId, col),
          isDynamic: false,
        };
      });

    const dynRows = dynamicKinds().map(({ kind, side, source, field }) => ({
      field,
      label: side ? `${kind} (${side})` : kind,
      value: null,  // Placeholder (updated live via transactions)
      isEdited: false,
      isControllable: false,
      isDynamic: true,
      source,
    }));

    const idRow = baseRows.find((r) => r.field === "id");
    const otherRows = baseRows.filter((r) => r.field !== "id");
    return [...(idRow ? [idRow] : []), ...dynRows, ...otherRows];
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

  const colDefs = createMemo((): ColDef[] => {
    return [
      {
        field: "label",
        headerName: "Property",
        flex: 1,
        editable: false,
        cellStyle: { fontFamily: "monospace", opacity: "0.7" },
        cellRenderer: (params: any) => {
          const el = document.createElement("div");
          el.className = "flex items-center gap-1.5 h-full";
          const label = document.createElement("span");
          label.style.fontFamily = "monospace";
          label.style.opacity = "0.7";
          label.innerText = params.data.kind ?? params.value;
          el.appendChild(label);
          if (params.data.isDynamic) {
            const badge = document.createElement("span");
            const source = params.data.source;
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
            el.appendChild(badge);
          }
          return el;
        },
      },
      {
        field: "value",
        headerName: "Value",
        flex: 1,
        cellStyle: { fontFamily: "monospace" },
        editable: (params) => params.data.isControllable,
        cellClass: (params) => {
          if (params.data.isEdited) return "ag-cell-edited";
          if (params.data.isControllable) return "ag-cell-editable-custom";
          return "";
        },
      },
    ]
  });

  onMount(() => {
    if (!containerRef) return;

    const options: GridOptions = {
      theme: agGridCustomTheme,
      columnDefs: colDefs(),
      rowData: rows(),
      defaultColDef: { resizable: true },
      domLayout: "autoHeight",
      getRowId: (p) => p.data.field,
      onCellValueChanged: (event) => {
        addEdit({
          rowId: props.elementId,
          column: event.data.field,
          originalValue: event.data.originalValue,
          newValue: event.newValue,
        });
      },
    };

    gridApi = createGrid(containerRef, options);
  });

  // Update col defs reactively
  createEffect(() => {
    const defs = colDefs();
    if (gridApi) gridApi.setGridOption("columnDefs", defs);
  });

  // Update rows reactively (base data + edits)
  createEffect(() => {
    const data = rows();
    if (!gridApi) return;
    gridApi.setGridOption("rowData", data);
    gridApi.refreshCells({ force: true });  // Force cellclass recompute once controllability is loaded
  });

  // Refresh cell styles when edits change
  createEffect(() => {
    pendingEdits();
    gridApi?.refreshCells({ force: true });
  });

  onCleanup(() => gridApi?.destroy());

  return (
    <>
      <Dialog open={props.open} onOpenChange={(o) => { if (!o) props.onClose(); }}>
        <Dialog.Portal>
          <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
          <div class="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
            <Dialog.Content class="pointer-events-auto w-full max-w-md max-h-[80vh] flex flex-col rounded-lg bg-[var(--popover-bg)] text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none">
              <div class="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] shrink-0">
                <Dialog.Title class="text-sm font-medium text-[var(--title-color)] font-mono">
                  {props.elementId}
                  <span class="ml-2 text-xs opacity-50">{props.componentType}</span>
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

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
            </Dialog.Content>
          </div>
        </Dialog.Portal>
      </Dialog>

      <Show when={showScadaPopup()}>
        <ScadaControlPopup
          open={showScadaPopup()}
          onClose={() => setShowScadaPopup(false)}
          edits={pendingEdits()}
          requester="single-element-popup"
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
    </>
  );
};
