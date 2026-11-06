/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createResource, For, Show, type Component } from "solid-js";
import { FiSearch, FiPlus, FiX, FiSettings, FiTrash2, FiEdit2 } from "solid-icons/fi";
import { TbTable } from "solid-icons/tb";
import { Dialog } from "@kobalte/core/dialog";
import { openInCentral } from "@/utils/openInCentral";
import { NetworkPropertiesPanel, CustomColumn, defaultComponentTypeConfig, ElementSchemaResponse } from "../types";
import { backendGet } from "@/services/backend";

const STORAGE_KEY = "network_properties_explorer_items";

const loadPanels = (): NetworkPropertiesPanel[] => {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as NetworkPropertiesPanel[];
    return raw.map((p) => ({
      ...p,
      params: {
        ...p.params,
        config: p.params.config ?? defaultComponentTypeConfig(),
      },
    }));
  } catch { return []; }
};

interface ConfigDialogState {
  open: boolean;
  panel: NetworkPropertiesPanel | null;
  allColumns: string[];
  visibleColumns: Set<string>;
  customColumns: CustomColumn[];
  newColName: string;
  newColExpr: string;
  editingIndex: number | null;
  exprError: string | null;
}

export const NetworkPropertiesExplorer: Component = () => {
  const [searchQuery, setSearchQuery] = createSignal("");
  const [panels, setPanels] = createSignal<NetworkPropertiesPanel[]>(loadPanels());
  const [createOpen, setCreateOpen] = createSignal(false);
  const [selectedType, setSelectedType] = createSignal<string | null>(null);
  const [typeSearch, setTypeSearch] = createSignal("");

  const [configDialog, setConfigDialog] = createSignal<ConfigDialogState>({
    open: false, panel: null, allColumns: [], visibleColumns: new Set(),
    customColumns: [], newColName: "", newColExpr: "", editingIndex: null, exprError: null,
  });

  const [componentTypes] = createResource(() => backendGet<string[]>("/network/component-types"));

  const filteredTypes = () =>
    (componentTypes() ?? []).filter((t) =>
      t.toLowerCase().includes(typeSearch().toLowerCase())
    );

  const filteredPanels = () =>
    panels().filter((p) =>
      p.params.componentType.toLowerCase().includes(searchQuery().toLowerCase())
    );

  const savePanels = (next: NetworkPropertiesPanel[]) => {
    setPanels(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  };

  const openViewer = (panel: NetworkPropertiesPanel) => {
    openInCentral({
      id: `network-properties-${panel.id}`,
      title: panel.name,
      elementTag: "network-properties-viewer",
      params: panel.params,
    });
  };

  const handleCreate = () => {
    const type = selectedType();
    if (!type) return;
    const existing = panels().find((p) => p.params.componentType === type);
    if (existing) { openViewer(existing); setCreateOpen(false); return; }
    const panel: NetworkPropertiesPanel = {
      id: `np-${Date.now()}`,
      name: type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      params: { componentType: type, config: defaultComponentTypeConfig() },
    };
    savePanels([panel, ...panels()]);
    openViewer(panel);
    setCreateOpen(false);
    setSelectedType(null);
    setTypeSearch("");
  };

  const handleDelete = (panel: NetworkPropertiesPanel, e: MouseEvent) => {
    e.stopPropagation();
    savePanels(panels().filter((p) => p.id !== panel.id));
  };

  const handleEditCustomColumn = (index: number) => {
    const col = configDialog().customColumns[index];
    setConfigDialog((prev) => ({
      ...prev,
      editingIndex: index,
      newColName: col.name,
      newColExpr: col.expression,
      exprError: null,
    }));
  };

  const handleCancelEdit = () => {
    setConfigDialog((prev) => ({
      ...prev, editingIndex: null, newColName: "", newColExpr: "", exprError: null,
    }));
  };

  const openConfigDialog = async (panel: NetworkPropertiesPanel, e: MouseEvent) => {
    e.stopPropagation();
    const schema = await backendGet<ElementSchemaResponse>(
      `/network/component-types-schema/${panel.params.componentType}`
    );
    const allColumns = schema.columns.filter((c) => c !== "id");
    const visible = panel.params.config.visibleColumns
      ? new Set(panel.params.config.visibleColumns)
      : new Set(allColumns);
    setConfigDialog({
      open: true,
      panel,
      allColumns,
      visibleColumns: visible,
      customColumns: [...panel.params.config.customColumns],
      newColName: "",
      newColExpr: "",
      editingIndex: null,
      exprError: null,
    });
  };

  const toggleColumnVisible = (col: string) => {
    setConfigDialog((prev) => {
      const next = new Set(prev.visibleColumns);
      if (next.has(col)) next.delete(col); else next.add(col);
      return { ...prev, visibleColumns: next };
    });
  };

  const validateExpression = (expr: string, columns: string[]): string | null => {
    try {
      const args = columns.map((c) => `${c} = 0`).join(", ");
      new Function(`let ${args}; return (${expr});`);
      return null;
    } catch (e: any) {
      return e.message;
    }
  };

  const handleAddCustomColumn = () => {
    const d = configDialog();
    const name = d.newColName.trim();
    const expr = d.newColExpr.trim();
    if (!name || !expr) return;
    const allCols = [...d.allColumns, ...d.customColumns.map((c) => c.name)];
    const err = validateExpression(expr, allCols);
    if (err) { setConfigDialog((prev) => ({ ...prev, exprError: err })); return; }

    if (d.editingIndex !== null) {
      setConfigDialog((prev) => ({
        ...prev,
        customColumns: prev.customColumns.map((c, i) =>
          i === prev.editingIndex ? { name, expression: expr } : c
        ),
        newColName: "",
        newColExpr: "",
        editingIndex: null,
        exprError: null,
      }));
    } else {
      setConfigDialog((prev) => ({
        ...prev,
        customColumns: [...prev.customColumns, { name, expression: expr }],
        newColName: "",
        newColExpr: "",
        exprError: null,
      }));
    }
  };

  const handleDeleteCustomColumn = (index: number) => {
    setConfigDialog((prev) => ({
      ...prev,
      customColumns: prev.customColumns.filter((_, i) => i !== index),
    }));
  };

  const handleSaveConfig = () => {
    const d = configDialog();
    if (!d.panel) return;
    const visibleColumns = d.visibleColumns.size === d.allColumns.length
      ? null
      : [...d.visibleColumns];
    const updatedPanel: NetworkPropertiesPanel = {
      ...d.panel,
      params: {
        ...d.panel.params,
        config: { visibleColumns, customColumns: d.customColumns },
      },
    };
    savePanels(panels().map((p) => p.id === updatedPanel.id ? updatedPanel : p));
    openViewer(updatedPanel);
    setConfigDialog((prev) => ({ ...prev, open: false }));
  };

  return (
    <>
      <div class="flex flex-col h-full w-full bg-sidebar-bg border-r border-border">
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
            onClick={() => setCreateOpen(true)}
            class="p-1.5 rounded-md text-fg hover:bg-sidebar-active-bg hover:text-links transition-colors shrink-0"
            title="Open element type"
          >
            <FiPlus class="size-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-bg">
          <Show
            when={filteredPanels().length > 0}
            fallback={<div class="p-4 text-center text-sm text-fg opacity-50 italic">No element types opened yet.</div>}
          >
            <For each={filteredPanels()}>
              {(panel) => (
                <div
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onClick={() => openViewer(panel)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") openViewer(panel); }}
                >
                  <div class="flex items-center gap-3 truncate">
                    <div class="text-icons group-hover:text-links transition-colors shrink-0">
                      <TbTable class="size-4" />
                    </div>
                    <div class="flex flex-col truncate">
                      <span class="font-medium text-sm text-fg truncate">{panel.name}</span>
                      <Show when={panel.params.config.customColumns.length > 0}>
                        <span class="text-[10px] text-fg opacity-50 font-mono">
                          +{panel.params.config.customColumns.length} custom col{panel.params.config.customColumns.length > 1 ? "s" : ""}
                        </span>
                      </Show>
                    </div>
                  </div>
                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => openConfigDialog(panel, e)}
                      class="p-1.5 hover:bg-icon-btn-bg-hover hover:text-links rounded text-icons transition-colors"
                      title="Configure columns"
                    >
                      <FiSettings class="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(panel, e)}
                      class="p-1.5 hover:bg-[var(--warning-bg)] hover:text-[var(--warning-icon)] rounded text-icons transition-colors"
                      title="Remove"
                    >
                      <FiX class="size-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </For>
          </Show>
        </div>
      </div>

      {/* Create dialog */}
      <Dialog open={createOpen()} onOpenChange={setCreateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
          <div class="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
            <Dialog.Content class="pointer-events-auto w-full max-w-sm rounded-lg bg-[var(--popover-bg)] p-6 text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none">
              <div class="flex items-center justify-between mb-4">
                <Dialog.Title class="text-lg font-medium text-[var(--title-color)]">
                  Open Element Type
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

              <input
                type="text"
                placeholder="Filter types..."
                value={typeSearch()}
                onInput={(e) => setTypeSearch(e.currentTarget.value)}
                autofocus
                class="w-full px-3 py-2 mb-3 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] focus:ring-1 focus:ring-[var(--links)] transition-all"
              />

              <div class="max-h-64 overflow-y-auto rounded border border-[var(--border)] mb-5 custom-scrollbar">
                <Show when={!componentTypes.loading} fallback={
                  <div class="p-4 text-center text-sm opacity-50">Loading...</div>
                }>
                  <For each={filteredTypes()}>
                    {(type) => (
                      <div
                        class={`px-3 py-2 text-sm cursor-pointer font-mono transition-colors ${
                          selectedType() === type
                            ? "bg-[var(--links)] text-white"
                            : "hover:bg-[var(--theme-hover)] text-[var(--fg)]"
                        }`}
                        onClick={() => setSelectedType(type)}
                      >
                        {type}
                      </div>
                    )}
                  </For>
                </Show>
              </div>

              <div class="flex justify-end gap-3">
                <button onClick={() => setCreateOpen(false)} class="px-4 py-2 text-sm font-medium rounded-md border border-[var(--border)] bg-[var(--search-btn-bg)] hover:bg-[var(--theme-hover)] transition-colors">Cancel</button>
                <button onClick={handleCreate} disabled={!selectedType()} class="px-4 py-2 text-sm font-medium rounded-md bg-[var(--links)] text-white hover:opacity-90 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed transition-all">Open</button>
              </div>
            </Dialog.Content>
          </div>
        </Dialog.Portal>
      </Dialog>

      {/* Configure dialog */}
      <Dialog open={configDialog().open} onOpenChange={(open) => setConfigDialog((prev) => ({ ...prev, open }))}>
        <Dialog.Portal>
          <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
          <div class="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
            <Dialog.Content class="pointer-events-auto w-full max-w-lg rounded-lg bg-[var(--popover-bg)] p-6 text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none">
              <div class="flex items-center justify-between mb-4">
                <Dialog.Title class="text-lg font-medium text-[var(--title-color)]">
                  Configure — {configDialog().panel?.name}
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

              {/* Column visibility */}
              <div class="mb-5">
                <div class="text-xs font-semibold uppercase tracking-wide text-[var(--fg)] opacity-60 mb-2">Visible Columns</div>
                <div class="max-h-40 overflow-y-auto rounded border border-[var(--border)] custom-scrollbar">
                  <For each={configDialog().allColumns}>
                    {(col) => (
                      <label class="flex items-center gap-2 px-3 py-1.5 hover:bg-[var(--theme-hover)] cursor-pointer text-sm font-mono">
                        <input
                          type="checkbox"
                          checked={configDialog().visibleColumns.has(col)}
                          onChange={() => toggleColumnVisible(col)}
                          class="accent-[var(--links)]"
                        />
                        {col}
                      </label>
                    )}
                  </For>
                </div>
                <div class="flex gap-2 mt-1.5">
                  <button
                    onClick={() => setConfigDialog((prev) => ({ ...prev, visibleColumns: new Set(prev.allColumns) }))}
                    class="text-xs text-[var(--links)] hover:opacity-70 transition-opacity"
                  >Select all</button>
                  <span class="text-xs opacity-30">·</span>
                  <button
                    onClick={() => setConfigDialog((prev) => ({ ...prev, visibleColumns: new Set() }))}
                    class="text-xs text-[var(--links)] hover:opacity-70 transition-opacity"
                  >Clear</button>
                </div>
              </div>

              {/* Custom columns list */}
              <Show when={configDialog().customColumns.length > 0}>
                <div class="rounded border border-[var(--border)] mb-3 divide-y divide-[var(--border)]">
                  <For each={configDialog().customColumns}>
                    {(col, i) => (
                      <div class={`flex items-center justify-between px-3 py-2 text-sm transition-colors ${configDialog().editingIndex === i() ? "bg-[var(--theme-hover)]" : ""}`}>
                        <div class="flex flex-col truncate">
                          <span class="font-mono text-[var(--code-text)]">{col.name}</span>
                          <span class="text-[10px] opacity-50 font-mono truncate">{col.expression}</span>
                        </div>
                        <div class="flex items-center gap-1 shrink-0 ml-2">
                          <button
                            onClick={() => handleEditCustomColumn(i())}
                            class="p-1 hover:bg-icon-btn-bg-hover hover:text-links rounded text-icons transition-colors"
                            title="Edit"
                          >
                            <FiEdit2 class="size-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteCustomColumn(i())}
                            class="p-1 hover:bg-[var(--warning-bg)] hover:text-[var(--warning-icon)] rounded text-icons transition-colors"
                            title="Delete"
                          >
                            <FiTrash2 class="size-3.5" />
                          </button>
                        </div>
                      </div>
                    )}
                  </For>
                </div>
              </Show>

              {/* Add/edit form */}
              <div class="flex gap-2 mb-1">
                <input
                  type="text"
                  placeholder="Column name"
                  value={configDialog().newColName}
                  onInput={(e) => setConfigDialog((prev) => ({ ...prev, newColName: e.currentTarget.value }))}
                  class="w-32 px-2 py-1.5 text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] font-mono"
                />
                <input
                  type="text"
                  placeholder="Expression (e.g. p1 + p2)"
                  value={configDialog().newColExpr}
                  onInput={(e) => setConfigDialog((prev) => ({ ...prev, newColExpr: e.currentTarget.value, exprError: null }))}
                  onKeyDown={(e) => { if (e.key === "Enter") handleAddCustomColumn(); if (e.key === "Escape") handleCancelEdit(); }}
                  class="flex-1 px-2 py-1.5 text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] font-mono"
                />
                <Show when={configDialog().editingIndex !== null}>
                  <button
                    onClick={handleCancelEdit}
                    class="px-2 py-1.5 text-xs rounded border border-[var(--border)] hover:bg-[var(--theme-hover)] shrink-0"
                    title="Cancel edit"
                  >
                    <FiX class="size-3.5" />
                  </button>
                </Show>
                <button
                  onClick={handleAddCustomColumn}
                  class="px-3 py-1.5 text-xs rounded bg-[var(--links)] text-white hover:opacity-90 shrink-0"
                >
                  {configDialog().editingIndex !== null ? "Save" : "Add"}
                </button>
              </div>
              <Show when={configDialog().exprError}>
                <div class="text-[11px] text-[var(--warning-icon)] font-mono mt-1">{configDialog().exprError}</div>
              </Show>
              <div class="text-[10px] opacity-40 mt-1 font-mono">
                Available: id, {configDialog().allColumns.join(", ")}
              </div>

              <div class="flex justify-end gap-3">
                <button onClick={() => setConfigDialog((prev) => ({ ...prev, open: false }))} class="px-4 py-2 text-sm font-medium rounded-md border border-[var(--border)] bg-[var(--search-btn-bg)] hover:bg-[var(--theme-hover)] transition-colors">Cancel</button>
                <button onClick={handleSaveConfig} class="px-4 py-2 text-sm font-medium rounded-md bg-[var(--links)] text-white hover:opacity-90 shadow-sm transition-all">Save</button>
              </div>
            </Dialog.Content>
          </div>
        </Dialog.Portal>
      </Dialog>
    </>
  );
};
