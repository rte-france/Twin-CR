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
  createResource,
  onMount,
  For,
  Show,
  type Component,
} from "solid-js";
import { FiSearch, FiPlus, FiEdit2, FiTrash2, FiX } from "solid-icons/fi";
import { openInCentral } from "@/utils/openInCentral";
import { Dialog } from "@kobalte/core/dialog";
import { createDefaultNad, Nad } from "../types";
import { AiOutlineShareAlt } from "solid-icons/ai";
import { backendGet } from "@/services/backend";

const STORAGE_KEY = "nad_explorer_items";

type DialogMode = "create" | "edit" | "delete";
interface DialogState {
  isOpen: boolean;
  mode: DialogMode;
  targetNad: Nad | null;
  inputValue: string;
  vlIds: string[];
  depth: number;
  layout: "default" | "geographical";
  radiusFactor: number;
}

interface VoltageLevel {
  vl_id: string;
  nominalVoltage: number;
}

interface SubstationEntry {
  substation_id: string;
  voltageLevels: VoltageLevel[];
}

async function fetchVoltageLevels(): Promise<VoltageLevel[]> {
  const data = await backendGet<SubstationEntry[]>("/substation-list").catch((e) => {
    throw new Error(`Failed to fetch voltage levels: ${e}`);
  });
  return data.flatMap((s) => s.voltageLevels);
}

export const NadExplorer: Component = () => {
  const [nads, setNads] = createSignal<Nad[]>([]);
  const [searchQuery, setSearchQuery] = createSignal("");
  const [vlSearch, setVlSearch] = createSignal("");
  const [voltageLevels] = createResource(fetchVoltageLevels);

  const [dialog, setDialog] = createSignal<DialogState>({
    isOpen: false,
    mode: "create",
    targetNad: null,
    inputValue: "",
    vlIds: [],
    depth: 1,
    layout: "default",
    radiusFactor: 500,
  });

  onMount(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setNads(JSON.parse(stored) as Nad[]);
      } catch (e) {
        setNads([]);
      }
    } else {
      const defaultNad = createDefaultNad(`nad-${Date.now()}`, "Example NAD");
      setNads([defaultNad]);
    }
  });

  createEffect(() => {
    if (nads().length > 0 || localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(nads()));
    }
  });

  const filteredNads = () =>
    nads().filter((d) =>
      d.name.toLowerCase().includes(searchQuery().toLowerCase()),
    );

  const filteredVls = () => {
    const q = vlSearch().toLowerCase();
    return (voltageLevels() ?? []).filter((v) =>
      v.vl_id.toLowerCase().includes(q),
    );
  };

  const toggleVl = (vlId: string) => {
    setDialog((prev) => {
      const already = prev.vlIds.includes(vlId);
      return {
        ...prev,
        vlIds: already
          ? prev.vlIds.filter((v) => v !== vlId)
          : [...prev.vlIds, vlId],
      };
    });
  };

  const handleOpenNad = (nad: Nad) => {
    openInCentral({
      id: `nad-${nad.id}`,
      title: nad.name,
      elementTag: "nad-viewer",
      params: {
        ...nad,
      },
    });
  };

  const openCreateDialog = () => {
    setVlSearch("");
    setDialog({
      isOpen: true,
      mode: "create",
      targetNad: null,
      inputValue: "",
      vlIds: [],
      depth: 1,
      layout: "default",
      radiusFactor: 500,
    });
  };

  const openEditDialog = (nad: Nad, e: MouseEvent) => {
    e.stopPropagation();
    setVlSearch("");
    setDialog({
      isOpen: true,
      mode: "edit",
      targetNad: nad,
      inputValue: nad.name,
      vlIds: nad.params.vlIds,
      depth: nad.params.depth,
      layout: nad.params.layout,
      radiusFactor: nad.params.radiusFactor,
    });
  };

  const openDeleteDialog = (nad: Nad, e: MouseEvent) => {
    e.stopPropagation();
    setDialog({
      isOpen: true,
      mode: "delete",
      targetNad: nad,
      inputValue: "",
      vlIds: [],
      depth: 1,
      layout: "default",
      radiusFactor: 500,
    });
  };

  const handleDialogSubmit = () => {
    const { mode, targetNad, inputValue, vlIds, depth, layout, radiusFactor } =
      dialog();
    const trimmedInput = inputValue.trim();

    if (mode === "create") {
      if (!trimmedInput) return;
      const newNad = createDefaultNad(`nad-${Date.now()}`, trimmedInput);
      newNad.params.vlIds = vlIds;
      newNad.params.depth = depth;
      newNad.params.layout = layout;
      newNad.params.radiusFactor = radiusFactor;
      setNads((prev) => [newNad, ...prev]);
      handleOpenNad(newNad);
    } else if (mode === "edit" && targetNad) {
      if (!trimmedInput) return;
      const updatedNad: Nad = {
        ...targetNad,
        name: trimmedInput,
        params: { ...targetNad.params, vlIds, depth, layout, radiusFactor },
      };
      setNads((prev) =>
        prev.map((n) => (n.id === targetNad.id ? updatedNad : n)),
      );
      handleOpenNad(updatedNad);
    } else if (mode === "delete" && targetNad) {
      setNads((prev) => prev.filter((n) => n.id !== targetNad.id));
    }

    setDialog((prev) => ({ ...prev, isOpen: false }));
  };

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
            title="New Nad"
          >
            <FiPlus class="size-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-bg">
          <Show
            when={filteredNads().length > 0}
            fallback={
              <div class="p-4 text-center text-sm text-fg opacity-50 italic">
                No Nad found.
              </div>
            }
          >
            <For each={filteredNads()}>
              {(nad) => (
                <div
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onClick={() => handleOpenNad(nad)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") handleOpenNad(nad);
                  }}
                >
                  <div class="flex items-center gap-3 truncate">
                    <div class="text-icons group-hover:text-links transition-colors shrink-0">
                      <AiOutlineShareAlt class="size-4" />
                    </div>
                    <div class="flex flex-col truncate">
                      <span class="font-medium text-sm text-fg truncate">
                        {nad.name}
                      </span>
                      <span class="text-[10px] text-fg opacity-50">
                        {nad.params.vlIds.length
                          ? `${nad.params.vlIds.length} VL(s) · depth ${nad.params.depth}`
                          : `All VLs · depth ${nad.params.depth}`}
                      </span>
                    </div>
                  </div>

                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => openEditDialog(nad, e)}
                      class="p-1.5 hover:bg-icon-btn-bg-hover hover:text-links rounded text-icons transition-colors"
                      title="Edit"
                    >
                      <FiEdit2 class="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => openDeleteDialog(nad, e)}
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
            <Dialog.Content class="pointer-events-auto w-full max-w-sm rounded-lg bg-[var(--popover-bg)] p-6 text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none animate-in fade-in zoom-in-95 duration-200">
              <div class="flex items-center justify-between mb-4">
                <Dialog.Title class="text-lg font-medium text-[var(--title-color)]">
                  {dialog().mode === "create" && "Create New Nad"}
                  {dialog().mode === "edit" && "Edit Nad"}
                  {dialog().mode === "delete" && "Delete Nad"}
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

              <Show when={dialog().mode === "delete"}>
                <Dialog.Description class="mb-5 text-sm opacity-80">
                  Are you sure you want to delete "{dialog().targetNad?.name}"?
                  This action cannot be undone.
                </Dialog.Description>
              </Show>

              <Show when={dialog().mode !== "delete"}>
                {/* Name */}
                <label class="block text-xs text-fg opacity-60 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={dialog().inputValue}
                  onInput={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      inputValue: e.currentTarget.value,
                    }))
                  }
                  placeholder="NAD name..."
                  autofocus
                  class="w-full px-3 py-2 mb-4 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] focus:ring-1 focus:ring-[var(--links)] transition-all"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleDialogSubmit();
                  }}
                />

                <label class="block text-xs text-fg opacity-60 mb-1">
                  Depth
                </label>
                <input
                  type="number"
                  min={0}
                  value={dialog().depth}
                  onInput={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      depth: Math.max(0, parseInt(e.currentTarget.value) || 0),
                    }))
                  }
                  class="w-full px-3 py-2 mb-4 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] transition-all"
                />

                <label class="block text-xs text-fg opacity-60 mb-1">
                  Layout
                </label>
                <select
                  value={dialog().layout}
                  onChange={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      layout: e.currentTarget.value as
                        | "default"
                        | "geographical",
                    }))
                  }
                  class="w-full px-3 py-2 mb-4 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] transition-all"
                >
                  <option value="default">Default</option>
                  <option value="geographical">Geographical</option>
                </select>

                <Show when={dialog().layout === "geographical"}>
                  <label class="block text-xs text-fg opacity-60 mb-1">
                    Radius factor
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={50}
                    value={dialog().radiusFactor}
                    onInput={(e) =>
                      setDialog((prev) => ({
                        ...prev,
                        radiusFactor: Math.max(
                          0,
                          parseInt(e.currentTarget.value) || 0,
                        ),
                      }))
                    }
                    class="w-full px-3 py-2 mb-4 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] transition-all"
                  />
                </Show>

                {/* VL selector */}
                <label class="block text-xs text-fg opacity-60 mb-1">
                  Voltage levels
                  <span class="ml-2 opacity-50">
                    {dialog().vlIds.length
                      ? `${dialog().vlIds.length} selected`
                      : "all"}
                  </span>
                </label>
                <div class="relative mb-1">
                  <FiSearch class="absolute left-2 top-1/2 -translate-y-1/2 size-3 opacity-40 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Filter voltage levels..."
                    value={vlSearch()}
                    onInput={(e) => setVlSearch(e.currentTarget.value)}
                    class="w-full pl-7 pr-2 py-1.5 text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] transition-all"
                  />
                </div>
                <div class="h-40 overflow-y-auto border border-[var(--border)] rounded-md bg-[var(--pre-bg)] mb-4">
                  <Show when={voltageLevels.loading}>
                    <p class="text-xs text-center opacity-50 p-4">
                      Loading voltage levels…
                    </p>
                  </Show>
                  <Show when={voltageLevels.error}>
                    <p class="text-xs text-center text-red-400 p-4">
                      Failed to load voltage levels
                    </p>
                  </Show>
                  <Show when={!voltageLevels.loading && !voltageLevels.error}>
                    <For each={filteredVls()}>
                      {(vl) => {
                        const selected = () =>
                          dialog().vlIds.includes(vl.vl_id);
                        return (
                          <div
                            class="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-[var(--theme-hover)] transition-colors"
                            classList={{ "text-[var(--links)]": selected() }}
                            onClick={() => toggleVl(vl.vl_id)}
                          >
                            <span class="w-3 shrink-0">
                              {selected() ? "✓" : ""}
                            </span>
                            <span class="truncate font-mono">{vl.vl_id}</span>
                          </div>
                        );
                      }}
                    </For>
                  </Show>
                </div>

                {/* Selected chips */}
                <Show when={dialog().vlIds.length > 0}>
                  <div class="flex flex-wrap gap-1 mb-4">
                    <For each={dialog().vlIds}>
                      {(vlId) => (
                        <span class="flex items-center gap-1 text-[10px] bg-[var(--links)] text-white rounded px-2 py-0.5">
                          {vlId}
                          <button
                            onClick={() => toggleVl(vlId)}
                            class="opacity-70 hover:opacity-100"
                          >
                            ✕
                          </button>
                        </span>
                      )}
                    </For>
                  </div>
                </Show>
              </Show>

              <div class="flex justify-end gap-3">
                <button
                  onClick={() =>
                    setDialog((prev) => ({ ...prev, isOpen: false }))
                  }
                  class="px-4 py-2 text-sm font-medium rounded-md border border-[var(--border)] bg-[var(--search-btn-bg)] hover:bg-[var(--theme-hover)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDialogSubmit}
                  class={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
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
