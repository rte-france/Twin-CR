/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the TwinEU-core project.
*/

import {
  createSignal,
  createEffect,
  createResource,
  createMemo,
  onMount,
  For,
  Index,
  Show,
  type Component,
} from "solid-js";
import { FiSearch, FiPlus, FiEdit2, FiTrash2, FiX } from "solid-icons/fi";
import { TbCircuitSwitchClosed } from "solid-icons/tb";
import { Dialog } from "@kobalte/core/dialog";
import { openInCentral } from "@/utils/openInCentral";
import { backendGet } from "@/services/backend";
import {
  createDefaultSldDiagram,
  layoutErrors,
  syncLayout,
  POSITION_STEP,
  type SldDiagram,
  type SldDiagramParams,
  type SldElementRef,
  type SldLayoutType,
} from "../types/SldDiagram";

const STORAGE_KEY = "sld_explorer_items";

type DialogMode = "create" | "edit" | "delete";

interface DialogState {
  isOpen: boolean;
  mode: DialogMode;
  target: SldDiagram | null;
  name: string;
  params: SldDiagramParams;
}

interface SubstationEntry {
  substation_id: string;
  voltageLevels: { vl_id: string; nominalVoltage: number }[];
}

const emptyDialog = (): DialogState => ({
  isOpen: false,
  mode: "create",
  target: null,
  name: "",
  params: createDefaultSldDiagram("", "").params,
});

async function fetchSubstations(): Promise<SubstationEntry[]> {
  return backendGet<SubstationEntry[]>("/substation-list").catch((e) => {
    throw new Error(`Failed to fetch substations: ${e}`);
  });
}

export const SldExplorer: Component = () => {
  const [diagrams, setDiagrams] = createSignal<SldDiagram[]>([]);
  const [searchQuery, setSearchQuery] = createSignal("");
  const [elementSearch, setElementSearch] = createSignal("");
  const [substations] = createResource(fetchSubstations);
  const [dialog, setDialog] = createSignal<DialogState>(emptyDialog());

  onMount(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setDiagrams(JSON.parse(stored) as SldDiagram[]);
      } catch {
        setDiagrams([]);
      }
    }
  });

  createEffect(() => {
    if (diagrams().length > 0 || localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(diagrams()));
    }
  });

  const filteredDiagrams = () =>
    diagrams().filter((d) =>
      d.name.toLowerCase().includes(searchQuery().toLowerCase()),
    );

  const filteredSubstations = () => {
    const q = elementSearch().toLowerCase();
    return (substations() ?? []).filter(
      (s) =>
        s.substation_id.toLowerCase().includes(q) ||
        s.voltageLevels.some((vl) => vl.vl_id.toLowerCase().includes(q)),
    );
  };

  const params = () => dialog().params;
  const elements = () => params().elements;
  const errors = createMemo(() => layoutErrors(params()));

  const updateParams = (next: (p: SldDiagramParams) => SldDiagramParams) =>
    setDialog((prev) => ({ ...prev, params: next(prev.params) }));

  const isSelected = (id: string) => elements().some((e) => e.id === id);

  const toggleElement = (element: SldElementRef) =>
    updateParams((p) =>
      syncLayout({
        ...p,
        elements: p.elements.some((e) => e.id === element.id)
          ? p.elements.filter((e) => e.id !== element.id)
          : [...p.elements, element],
      }),
    );

  const setCell = (row: number, col: number, id: string) =>
    updateParams((p) => ({
      ...p,
      matrix: p.matrix.map((cells, r) =>
        r === row ? cells.map((cell, c) => (c === col ? id : cell)) : cells,
      ),
    }));

  const columnCount = () => Math.max(1, ...params().matrix.map((r) => r.length));

  const addRow = () =>
    updateParams((p) => ({
      ...p,
      matrix: [...p.matrix, Array<string>(columnCount()).fill("")],
    }));

  const removeRow = (row: number) =>
    updateParams((p) => ({
      ...p,
      matrix: p.matrix.filter((_, r) => r !== row),
    }));

  const addColumn = () =>
    updateParams((p) => ({ ...p, matrix: p.matrix.map((r) => [...r, ""]) }));

  const removeColumn = () =>
    updateParams((p) => ({
      ...p,
      matrix: p.matrix.map((r) => r.slice(0, Math.max(1, r.length - 1))),
    }));

  const setPosition = (id: string, axis: "x" | "y", value: number) =>
    updateParams((p) => ({
      ...p,
      positions: { ...p.positions, [id]: { ...p.positions[id], [axis]: value } },
    }));

  const handleOpen = (diagram: SldDiagram) => {
    openInCentral({
      id: `sld-${diagram.id}`,
      title: diagram.name,
      elementTag: "sld-viewer",
      params: { ...diagram },
    });
  };

  const openCreateDialog = () => {
    setElementSearch("");
    setDialog({ ...emptyDialog(), isOpen: true, mode: "create" });
  };

  const openEditDialog = (diagram: SldDiagram, e: MouseEvent) => {
    e.stopPropagation();
    setElementSearch("");
    setDialog({
      isOpen: true,
      mode: "edit",
      target: diagram,
      name: diagram.name,
      params: syncLayout(diagram.params),
    });
  };

  const openDeleteDialog = (diagram: SldDiagram, e: MouseEvent) => {
    e.stopPropagation();
    setDialog({ ...emptyDialog(), isOpen: true, mode: "delete", target: diagram });
  };

  const canSubmit = () => {
    const { mode, name } = dialog();
    if (mode === "delete") return true;
    return name.trim().length > 0 && elements().length > 0 && errors().length === 0;
  };

  const handleDialogSubmit = () => {
    const { mode, target, name } = dialog();
    if (mode !== "delete" && !canSubmit()) return;

    if (mode === "create") {
      const diagram: SldDiagram = {
        ...createDefaultSldDiagram(`sld-${Date.now()}`, name.trim()),
        params: params(),
      };
      setDiagrams((prev) => [diagram, ...prev]);
      handleOpen(diagram);
    } else if (mode === "edit" && target) {
      const diagram: SldDiagram = { ...target, name: name.trim(), params: params() };
      setDiagrams((prev) => prev.map((d) => (d.id === target.id ? diagram : d)));
      handleOpen(diagram);
    } else if (mode === "delete" && target) {
      setDiagrams((prev) => prev.filter((d) => d.id !== target.id));
    }

    setDialog((prev) => ({ ...prev, isOpen: false }));
  };

  const inputClass =
    "w-full px-3 py-2 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] transition-all";

  return (
    <>
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
            onClick={openCreateDialog}
            class="p-1.5 rounded-md text-fg hover:bg-sidebar-active-bg hover:text-links transition-colors shrink-0"
            title="New diagram"
          >
            <FiPlus class="size-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-bg">
          <Show
            when={filteredDiagrams().length > 0}
            fallback={
              <div class="p-4 text-center text-sm text-fg opacity-50 italic">
                No diagram found.
              </div>
            }
          >
            <For each={filteredDiagrams()}>
              {(diagram) => (
                <div
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onClick={() => handleOpen(diagram)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") handleOpen(diagram);
                  }}
                >
                  <div class="flex items-center gap-3 truncate">
                    <div class="text-icons group-hover:text-links transition-colors shrink-0">
                      <TbCircuitSwitchClosed class="size-4" />
                    </div>
                    <div class="flex flex-col truncate">
                      <span class="font-medium text-sm text-fg truncate">
                        {diagram.name}
                      </span>
                      <span class="text-[10px] text-fg opacity-50">
                        {diagram.params.elements.length} element(s) ·{" "}
                        {diagram.params.elements.length > 1
                          ? diagram.params.layoutType
                          : "single"}
                      </span>
                    </div>
                  </div>

                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => openEditDialog(diagram, e)}
                      class="p-1.5 hover:bg-icon-btn-bg-hover hover:text-links rounded text-icons transition-colors"
                      title="Edit"
                    >
                      <FiEdit2 class="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => openDeleteDialog(diagram, e)}
                      class="p-1.5 hover:bg-[var(--warning-bg)] hover:text-[var(--warning-icon)] rounded text-icons transition-colors"
                      title="Delete"
                    >
                      <FiTrash2 class="size-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </For>
          </Show>
        </div>
      </div>

      <Dialog
        open={dialog().isOpen}
        onOpenChange={(isOpen) => setDialog((prev) => ({ ...prev, isOpen }))}
      >
        <Dialog.Portal>
          <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
          <div class="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
            <Dialog.Content class="pointer-events-auto w-full max-w-lg max-h-[90vh] overflow-y-auto custom-scrollbar rounded-lg bg-[var(--popover-bg)] p-6 text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none animate-in fade-in zoom-in-95 duration-200">
              <div class="flex items-center justify-between mb-4">
                <Dialog.Title class="text-lg font-medium text-[var(--title-color)]">
                  {dialog().mode === "create" && "Create New Diagram"}
                  {dialog().mode === "edit" && "Edit Diagram"}
                  {dialog().mode === "delete" && "Delete Diagram"}
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

              <Show when={dialog().mode === "delete"}>
                <Dialog.Description class="mb-5 text-sm opacity-80">
                  Are you sure you want to delete "{dialog().target?.name}"? This
                  action cannot be undone.
                </Dialog.Description>
              </Show>

              <Show when={dialog().mode !== "delete"}>
                <label class="block text-xs text-fg opacity-60 mb-1">Name</label>
                <input
                  type="text"
                  value={dialog().name}
                  onInput={(e) =>
                    setDialog((prev) => ({ ...prev, name: e.currentTarget.value }))
                  }
                  placeholder="Diagram name..."
                  autofocus
                  class={`${inputClass} mb-4`}
                />

                {/* Element picker */}
                <label class="block text-xs text-fg opacity-60 mb-1">
                  Substations and voltage levels
                  <span class="ml-2 opacity-50">
                    {elements().length} selected
                  </span>
                </label>
                <div class="relative mb-1">
                  <FiSearch class="absolute left-2 top-1/2 -translate-y-1/2 size-3 opacity-40 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Filter substations and voltage levels..."
                    value={elementSearch()}
                    onInput={(e) => setElementSearch(e.currentTarget.value)}
                    class="w-full pl-7 pr-2 py-1.5 text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] transition-all"
                  />
                </div>
                <div class="h-40 overflow-y-auto border border-[var(--border)] rounded-md bg-[var(--pre-bg)] mb-4 custom-scrollbar">
                  <Show when={substations.loading}>
                    <p class="text-xs text-center opacity-50 p-4">
                      Loading substations…
                    </p>
                  </Show>
                  <Show when={substations.error}>
                    <p class="text-xs text-center text-red-400 p-4">
                      Failed to load substations
                    </p>
                  </Show>
                  <Show when={!substations.loading && !substations.error}>
                    <For each={filteredSubstations()}>
                      {(substation) => (
                        <>
                          <div
                            class="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-[var(--theme-hover)] transition-colors"
                            classList={{
                              "text-[var(--links)]": isSelected(
                                substation.substation_id,
                              ),
                            }}
                            onClick={() =>
                              toggleElement({
                                id: substation.substation_id,
                                type: "sub",
                              })
                            }
                          >
                            <span class="w-3 shrink-0">
                              {isSelected(substation.substation_id) ? "✓" : ""}
                            </span>
                            <span class="truncate font-mono">
                              {substation.substation_id}
                            </span>
                          </div>
                          <For each={substation.voltageLevels}>
                            {(vl) => (
                              <div
                                class="flex items-center gap-2 pl-8 pr-3 py-1 text-xs cursor-pointer hover:bg-[var(--theme-hover)] transition-colors"
                                classList={{
                                  "text-[var(--links)]": isSelected(vl.vl_id),
                                }}
                                onClick={() =>
                                  toggleElement({ id: vl.vl_id, type: "vl" })
                                }
                              >
                                <span class="w-3 shrink-0">
                                  {isSelected(vl.vl_id) ? "✓" : ""}
                                </span>
                                <span class="truncate font-mono opacity-70">
                                  {vl.vl_id}
                                </span>
                              </div>
                            )}
                          </For>
                        </>
                      )}
                    </For>
                  </Show>
                </div>

                {/* Layout, only meaningful from two elements on */}
                <Show
                  when={elements().length > 1}
                  fallback={
                    <p class="text-xs opacity-50 mb-4">
                      Select a second element to choose a layout.
                    </p>
                  }
                >
                  <label class="block text-xs text-fg opacity-60 mb-1">
                    Layout
                  </label>
                  <select
                    value={params().layoutType}
                    onChange={(e) =>
                      updateParams((p) => ({
                        ...p,
                        layoutType: e.currentTarget.value as SldLayoutType,
                      }))
                    }
                    class={`${inputClass} mb-4`}
                  >
                    <option value="matrix">Matrix</option>
                    <option value="positioned">Positioned</option>
                  </select>

                  <Show when={params().layoutType === "matrix"}>
                    <div class="flex items-center justify-between mb-1">
                      <label class="block text-xs text-fg opacity-60">
                        Grid
                      </label>
                      <div class="flex gap-1">
                        <button
                          onClick={addRow}
                          class="px-2 py-0.5 text-[10px] rounded border border-[var(--border)] hover:bg-[var(--theme-hover)]"
                        >
                          + row
                        </button>
                        <button
                          onClick={addColumn}
                          class="px-2 py-0.5 text-[10px] rounded border border-[var(--border)] hover:bg-[var(--theme-hover)]"
                        >
                          + col
                        </button>
                        <button
                          onClick={removeColumn}
                          class="px-2 py-0.5 text-[10px] rounded border border-[var(--border)] hover:bg-[var(--theme-hover)]"
                        >
                          − col
                        </button>
                      </div>
                    </div>
                    <div class="space-y-1 mb-2">
                      <Index each={params().matrix}>
                        {(row, rowIndex) => (
                          <div class="flex items-center gap-1">
                            <Index each={row()}>
                              {(cell, colIndex) => (
                                <select
                                  onChange={(e) =>
                                    setCell(
                                      rowIndex,
                                      colIndex,
                                      e.currentTarget.value,
                                    )
                                  }
                                  class="flex-1 min-w-0 px-1 py-1 text-[11px] font-mono bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded text-[var(--code-text)] focus:outline-none focus:border-[var(--links)]"
                                >
                                  {/* Solid applies a select's value before the options exist, so each option carries its own selected state */}
                                  <option value="" selected={cell() === ""}>
                                    —
                                  </option>
                                  <For each={elements()}>
                                    {(element) => (
                                      <option
                                        value={element.id}
                                        selected={cell() === element.id}
                                      >
                                        {element.id}
                                      </option>
                                    )}
                                  </For>
                                </select>
                              )}
                            </Index>
                            <button
                              onClick={() => removeRow(rowIndex)}
                              class="p-1 text-icons hover:text-[var(--warning-icon)] shrink-0"
                              title="Remove row"
                            >
                              <FiTrash2 class="size-3" />
                            </button>
                          </div>
                        )}
                      </Index>
                    </div>
                  </Show>

                  <Show when={params().layoutType === "positioned"}>
                    <label class="block text-xs text-fg opacity-60 mb-1">
                      Top-left corner of each element
                    </label>
                    <div class="space-y-1 mb-2">
                      <For each={elements()}>
                        {(element) => (
                          <div class="flex items-center gap-2">
                            <span
                              class="flex-1 min-w-0 truncate text-[11px] font-mono"
                              title={element.id}
                            >
                              {element.id}
                            </span>
                            <input
                              type="number"
                              step={POSITION_STEP}
                              value={params().positions[element.id]?.x ?? 0}
                              onInput={(e) =>
                                setPosition(
                                  element.id,
                                  "x",
                                  parseFloat(e.currentTarget.value) || 0,
                                )
                              }
                              class="w-20 px-2 py-1 text-[11px] bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded text-[var(--code-text)] focus:outline-none focus:border-[var(--links)]"
                            />
                            <input
                              type="number"
                              step={POSITION_STEP}
                              value={params().positions[element.id]?.y ?? 0}
                              onInput={(e) =>
                                setPosition(
                                  element.id,
                                  "y",
                                  parseFloat(e.currentTarget.value) || 0,
                                )
                              }
                              class="w-20 px-2 py-1 text-[11px] bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded text-[var(--code-text)] focus:outline-none focus:border-[var(--links)]"
                            />
                            <button
                              onClick={() => toggleElement(element)}
                              class="p-1 text-icons hover:text-[var(--warning-icon)] shrink-0"
                              title="Remove element"
                            >
                              <FiTrash2 class="size-3" />
                            </button>
                          </div>
                        )}
                      </For>
                    </div>
                  </Show>
                </Show>

                <Show when={errors().length > 0}>
                  <p class="text-[11px] text-[var(--warning-icon)] mb-4">
                    Place each element exactly once in the grid:{" "}
                    {errors().join(", ")}
                  </p>
                </Show>
              </Show>

              <div class="flex justify-end gap-3">
                <button
                  onClick={() => setDialog((prev) => ({ ...prev, isOpen: false }))}
                  class="px-4 py-2 text-sm font-medium rounded-md border border-[var(--border)] bg-[var(--search-btn-bg)] hover:bg-[var(--theme-hover)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDialogSubmit}
                  disabled={!canSubmit()}
                  class={`px-4 py-2 text-sm font-medium rounded-md transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                    dialog().mode === "delete"
                      ? "bg-[var(--warning-bg)] text-[var(--warning-icon)] border border-[var(--warning-border)] hover:bg-opacity-80"
                      : "bg-[var(--links)] text-white hover:opacity-90 shadow-sm"
                  }`}
                >
                  {dialog().mode === "delete" ? "Delete" : "Save"}
                </button>
              </div>
            </Dialog.Content>
          </div>
        </Dialog.Portal>
      </Dialog>
    </>
  );
};
