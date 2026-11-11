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
import { IflParams } from "../types";
import { AiOutlineShareAlt } from "solid-icons/ai";
import { backendGet } from "@/services/backend";

const STORAGE_KEY = "ifl_explorer_items";

type DialogMode = "create" | "edit" | "delete";

interface DialogState {
  isOpen: boolean;
  mode: DialogMode;
  targetIfl: IflParams | null;
  inputValue: string;
  nodeIds: string[];
  depth: number;
}

const fetchNodes = (): Promise<string[]> =>
  backendGet<string[]>("/ifl-nodes").catch((e) => {
    throw new Error(`Failed to fetch nodes: ${e}`);
  });

export const IflExplorer: Component = () => {
  const [ifls, setIfls] = createSignal<IflParams[]>([]);
  const [searchQuery, setSearchQuery] = createSignal("");
  const [nodeSearch, setNodeSearch] = createSignal("");
  const [nodes] = createResource(fetchNodes);
  const [dialog, setDialog] = createSignal<DialogState>({
    isOpen: false,
    mode: "create",
    targetIfl: null,
    inputValue: "",
    nodeIds: [],
    depth: 0,
  });

  onMount(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setIfls(JSON.parse(stored) as IflParams[]);
      } catch (e) {
        console.error(e);
        localStorage.removeItem(STORAGE_KEY);
        setIfls([]);
      }
    } else {
      setIfls([
        {
          id: `ifl-${Date.now()}`,
          name: "Example IflParams 1",
          nodeIds: [],
          depth: 1,
        },
      ]);
    }
  });

  createEffect(() => {
    if (ifls().length > 0 || localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ifls()));
    }
  });

  const filteredIfls = () =>
    ifls().filter((d) =>
      d.name.toLowerCase().includes(searchQuery().toLowerCase()),
    );

  const filteredNodes = () => {
    const q = nodeSearch().toLowerCase();
    return (nodes() ?? []).filter((n) => n.toLowerCase().includes(q));
  };

  const toggleNode = (nodeId: string) => {
    setDialog((prev) => {
      const already = prev.nodeIds.includes(nodeId);
      return {
        ...prev,
        nodeIds: already
          ? prev.nodeIds.filter((n) => n !== nodeId)
          : [...prev.nodeIds, nodeId],
      };
    });
  };

  const handleOpenIfl = (ifl: IflParams) => {
    openInCentral({
      id: `ifl-${ifl.id}`,
      title: ifl.name,
      elementTag: "ifl-viewer",
      params: {
        id: ifl.id,
        name: ifl.name,
        nodeIds: ifl.nodeIds,
        depth: ifl.depth,
      },
    });
  };

  const openCreateDialog = () => {
    setNodeSearch("");
    setDialog({
      isOpen: true,
      mode: "create",
      targetIfl: null,
      inputValue: "",
      nodeIds: [],
      depth: 0,
    });
  };

  const openEditDialog = (ifl: IflParams, e: MouseEvent) => {
    e.stopPropagation();
    setNodeSearch("");
    setDialog({
      isOpen: true,
      mode: "edit",
      targetIfl: ifl,
      inputValue: ifl.name,
      nodeIds: ifl.nodeIds,
      depth: ifl.depth,
    });
  };

  const openDeleteDialog = (ifl: IflParams, e: MouseEvent) => {
    e.stopPropagation();
    setDialog({
      isOpen: true,
      mode: "delete",
      targetIfl: ifl,
      inputValue: "",
      nodeIds: [],
      depth: 0,
    });
  };

  const handleDialogSubmit = () => {
    const { mode, targetIfl, inputValue, nodeIds, depth } = dialog();
    const trimmedInput = inputValue.trim();

    if (mode === "create") {
      if (!trimmedInput) return;
      const newIfl: IflParams = {
        id: `ifl-${Date.now()}`,
        name: trimmedInput,
        nodeIds,
        depth,
      };
      setIfls((prev) => [newIfl, ...prev]);
      handleOpenIfl(newIfl);
    } else if (mode === "edit" && targetIfl) {
      if (!trimmedInput) return;
      const updatedIfl: IflParams = {
        id: targetIfl.id,
        name: trimmedInput,
        nodeIds,
        depth,
      };
      setIfls((prev) =>
        prev.map((n) => (n.id === targetIfl.id ? updatedIfl : n)),
      );
      handleOpenIfl(updatedIfl);
    } else if (mode === "delete" && targetIfl) {
      setIfls((prev) => prev.filter((n) => n.id !== targetIfl.id));
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
            title="New information flow model grapg"
          >
            <FiPlus class="size-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-bg">
          <Show
            when={filteredIfls().length > 0}
            fallback={
              <div class="p-4 text-center text-sm text-fg opacity-50 italic">
                No information flow model graph found.
              </div>
            }
          >
            <For each={filteredIfls()}>
              {(ifl) => (
                <div
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onClick={() => handleOpenIfl(ifl)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") handleOpenIfl(ifl);
                  }}
                >
                  <div class="flex items-center gap-3 truncate">
                    <div class="text-icons group-hover:text-links transition-colors shrink-0">
                      <AiOutlineShareAlt class="size-4" />
                    </div>
                    <div class="flex flex-col truncate">
                      <span class="font-medium text-sm text-fg truncate">
                        {ifl.name}
                      </span>
                      <span class="text-[10px] text-fg opacity-50">
                        {ifl.nodeIds.length
                          ? `${ifl.nodeIds.length} node(s) · depth ${ifl.depth}`
                          : `Full graph · depth ${ifl.depth}`}
                      </span>
                    </div>
                  </div>
                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => openEditDialog(ifl, e)}
                      class="p-1.5 hover:bg-icon-btn-bg-hover hover:text-links rounded text-icons transition-colors"
                      title="Edit"
                    >
                      <FiEdit2 class="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => openDeleteDialog(ifl, e)}
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
            <Dialog.Content class="pointer-events-auto w-full max-w-md rounded-lg bg-[var(--popover-bg)] p-6 text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none animate-in fade-in zoom-in-95 duration-200">
              <div class="flex items-center justify-between mb-4">
                <Dialog.Title class="text-lg font-medium text-[var(--title-color)]">
                  {dialog().mode === "create" && "Create New IFL graph"}
                  {dialog().mode === "edit" && "Edit IFL graph"}
                  {dialog().mode === "delete" && "Delete IFL graph"}
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

              <Show when={dialog().mode === "delete"}>
                <Dialog.Description class="mb-5 text-sm opacity-80">
                  Are you sure you want to delete "{dialog().targetIfl?.name}"?
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
                  placeholder="IFL graph name..."
                  autofocus
                  class="w-full px-3 py-2 mb-4 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] focus:ring-1 focus:ring-[var(--links)] transition-all"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleDialogSubmit();
                  }}
                />

                {/* Depth */}
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

                {/* Node selector */}
                <label class="block text-xs text-fg opacity-60 mb-1">
                  Nodes
                  <span class="ml-2 opacity-50">
                    {dialog().nodeIds.length
                      ? `${dialog().nodeIds.length} selected`
                      : "all (no filter)"}
                  </span>
                </label>
                <div class="relative mb-1">
                  <FiSearch class="absolute left-2 top-1/2 -translate-y-1/2 size-3 opacity-40 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Filter nodes..."
                    value={nodeSearch()}
                    onInput={(e) => setNodeSearch(e.currentTarget.value)}
                    class="w-full pl-7 pr-2 py-1.5 text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] transition-all"
                  />
                </div>
                <div class="h-40 overflow-y-auto border border-[var(--border)] rounded-md bg-[var(--pre-bg)] mb-4">
                  <Show when={nodes.loading}>
                    <p class="text-xs text-center opacity-50 p-4">
                      Loading nodes…
                    </p>
                  </Show>
                  <Show when={nodes.error}>
                    <p class="text-xs text-center text-red-400 p-4">
                      Failed to load nodes
                    </p>
                  </Show>
                  <Show when={!nodes.loading && !nodes.error}>
                    <For each={filteredNodes()}>
                      {(node) => {
                        const selected = () => dialog().nodeIds.includes(node);
                        return (
                          <div
                            class="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-[var(--theme-hover)] transition-colors"
                            classList={{ "text-[var(--links)]": selected() }}
                            onClick={() => toggleNode(node)}
                          >
                            <span class="w-3 shrink-0">
                              {selected() ? "✓" : ""}
                            </span>
                            <span class="truncate font-mono">{node}</span>
                          </div>
                        );
                      }}
                    </For>
                  </Show>
                </div>

                {/* Selected chips */}
                <Show when={dialog().nodeIds.length > 0}>
                  <div class="flex flex-wrap gap-1 mb-4">
                    <For each={dialog().nodeIds}>
                      {(nodeId) => (
                        <span class="flex items-center gap-1 text-[10px] bg-[var(--links)] text-white rounded px-2 py-0.5">
                          {nodeId}
                          <button
                            onClick={() => toggleNode(nodeId)}
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
