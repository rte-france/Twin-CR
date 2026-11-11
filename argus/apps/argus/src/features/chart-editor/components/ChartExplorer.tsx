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
  For,
  Show,
  type Component,
} from "solid-js";
import { FiSearch, FiPlus, FiEdit2, FiTrash2, FiX } from "solid-icons/fi";
import { openInCentral } from "@/utils/openInCentral";
import { Dialog } from "@kobalte/core/dialog";
import { type Chart } from "../types";
import { AiOutlineLineChart } from "solid-icons/ai";

const STORAGE_KEY = "chart_dashboards";

type DialogMode = "create" | "delete";
interface DialogState {
  isOpen: boolean;
  mode: DialogMode;
  targetDash: Chart | null;
  inputValue: string;
}

export const ChartExplorer: Component = () => {
  const [dashboards, setDashboards] = createSignal<Chart[]>([]);
  const [searchQuery, setSearchQuery] = createSignal<string>("");

  const [dialog, setDialog] = createSignal<DialogState>({
    isOpen: false,
    mode: "create",
    targetDash: null,
    inputValue: "",
  });

  const [editingId, setEditingId] = createSignal<string | null>(null);
  const [editInputValue, setEditInputValue] = createSignal<string>("");

  onMount(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setDashboards(JSON.parse(stored) as Chart[]);
      } catch (e) {
        setDashboards([]);
      }
    } else {
      setDashboards([
        {
          id: `dash-${Date.now()}`,
          name: "Sample Curve",
          topic: "S_4011",
        },
      ]);
    }
  });

  createEffect(() => {
    if (dashboards().length > 0 || localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(dashboards()));
    }
  });

  const filteredDashboards = () =>
    dashboards().filter((d) =>
      d.name.toLowerCase().includes(searchQuery().toLowerCase()),
    );

  const handleOpenViewer = (dashboard: Chart) => {
    if (editingId() === dashboard.id) return;

    openInCentral({
      id: `viewer-${dashboard.id}`,
      title: dashboard.name,
      elementTag: "curve-viewer",
      params: {
        dashboardId: dashboard.id,
        title: dashboard.name,
      },
    });
  };

  const openCreateDialog = () => {
    setDialog({
      isOpen: true,
      mode: "create",
      targetDash: null,
      inputValue: "",
    });
  };

  const openDeleteDialog = (dash: Chart, e: MouseEvent) => {
    e.stopPropagation();
    setDialog({
      isOpen: true,
      mode: "delete",
      targetDash: dash,
      inputValue: "",
    });
  };

  const startInlineEditing = (dash: Chart, e: MouseEvent) => {
    e.stopPropagation();
    setEditingId(dash.id);
    setEditInputValue(dash.name);
  };

  const commitInlineEditing = () => {
    const currentId = editingId();
    if (!currentId) return;

    const trimmedInput = editInputValue().trim();
    if (trimmedInput) {
      setDashboards((prev) =>
        prev.map((d) =>
          d.id === currentId ? { ...d, name: trimmedInput } : d,
        ),
      );
    }
    setEditingId(null);
  };

  const cancelInlineEditing = () => {
    setEditingId(null);
  };

  const handleDialogSubmit = () => {
    const { mode, targetDash, inputValue } = dialog();
    const trimmedInput = inputValue.trim();

    if (mode === "create") {
      if (!trimmedInput) return;
      const newDash: Chart = {
        id: `dash-${Date.now()}`,
        name: trimmedInput,
        topic: "",
      };
      setDashboards((prev) => [newDash, ...prev]);
      handleOpenViewer(newDash);
    } else if (mode === "delete" && targetDash) {
      setDashboards((prev) => prev.filter((d) => d.id !== targetDash.id));
    }

    setDialog((prev) => ({ ...prev, isOpen: false }));
  };

  return (
    <>
      <div class="flex flex-col h-full w-full bg-sidebar-bg">
        <div class="flex items-center gap-2 p-2 h-9 border-b border-border">
          <div class="relative flex-1 flex items-center">
            <FiSearch class="absolute left-2 size-3 text-[var(--fg)] opacity-50 pointer-events-none" />
            <input
              type="text"
              placeholder="Search curves..."
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
              class="w-32 lg:w-40 pl-7 pr-2 py-1 text-[11px] font-mono bg-bg border border-[var(--border)] rounded transition-colors focus:outline-none focus:border-[var(--links)] text-[var(--fg)] placeholder:opacity-40"
            />
          </div>
          <button
            onClick={openCreateDialog}
            class="p-1.5 rounded-md text-fg hover:bg-sidebar-active-bg hover:text-links transition-colors shrink-0"
            title="New Dashboard"
          >
            <FiPlus class="size-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-bg">
          <Show
            when={filteredDashboards().length > 0}
            fallback={
              <div class="p-4 text-center text-sm text-fg opacity-50 italic">
                No curve found.
              </div>
            }
          >
            <For each={filteredDashboards()}>
              {(dash) => (
                <div
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onClick={() => handleOpenViewer(dash)}
                  title="Open Viewer"
                >
                  <div class="flex items-center gap-3 truncate w-full">
                    <div class="text-fg opacity-60 group-hover:text-links group-hover:opacity-100 transition-colors shrink-0">
                      <AiOutlineLineChart class="size-4" />
                    </div>

                    <div class="flex flex-col truncate w-full">
                      <Show
                        when={editingId() === dash.id}
                        fallback={
                          <span class="font-medium text-sm text-fg truncate">
                            {dash.name}
                          </span>
                        }
                      >
                        <input
                          ref={(el) => setTimeout(() => el.focus(), 0)}
                          type="text"
                          value={editInputValue()}
                          onInput={(e) =>
                            setEditInputValue(e.currentTarget.value)
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitInlineEditing();
                            if (e.key === "Escape") cancelInlineEditing();
                          }}
                          onBlur={commitInlineEditing}
                          onClick={(e) => e.stopPropagation()}
                          class="font-medium text-sm text-fg bg-[var(--pre-bg)] border border-[var(--links)] rounded px-1 -ml-1 outline-none w-full max-w-[150px]"
                        />
                      </Show>

                      <Show when={dash.topic}>
                        <span class="text-[10px] text-fg opacity-50 truncate font-mono mt-0.5">
                          Topic: {dash.topic}
                        </span>
                      </Show>
                    </div>
                  </div>

                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                    <button
                      onClick={(e) => startInlineEditing(dash, e)}
                      class="p-1.5 hover:bg-media-bg hover:text-blue-400 rounded text-fg transition-colors"
                      title="Rename"
                    >
                      <FiEdit2 class="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => openDeleteDialog(dash, e)}
                      class="p-1.5 hover:bg-media-bg hover:text-warning-icon rounded text-fg transition-colors"
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
                  {dialog().mode === "create" && "Create New Curve"}
                  {dialog().mode === "delete" && "Delete Curve"}
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

              <Dialog.Description class="mb-5 text-sm opacity-80">
                {dialog().mode === "delete"
                  ? `Are you sure you want to delete "${dialog().targetDash?.name}"? This action cannot be undone.`
                  : "Please enter a name for your curve."}
              </Dialog.Description>

              <Show when={dialog().mode === "create"}>
                <input
                  type="text"
                  value={dialog().inputValue}
                  onInput={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      inputValue: e.currentTarget.value,
                    }))
                  }
                  placeholder="Curve name..."
                  autofocus
                  class="w-full px-3 py-2 mb-6 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] focus:ring-1 focus:ring-[var(--links)] transition-all"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleDialogSubmit();
                  }}
                />
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
