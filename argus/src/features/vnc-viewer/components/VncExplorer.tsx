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
import { VncPanel } from "../types";
import { TbDeviceDesktop } from "solid-icons/tb";

const STORAGE_KEY = "vnc_explorer_items";
const DEFAULT_VNC_URL = "http://localhost:6080/vnc.html";

type DialogMode = "create" | "edit" | "delete";
interface DialogState {
  isOpen: boolean;
  mode: DialogMode;
  targetVnc: VncPanel | null;
  inputValue: string;
  urlValue: string;
}

export const VncExplorer: Component = () => {
  const [vncs, setVncs] = createSignal<VncPanel[]>([]);
  const [searchQuery, setSearchQuery] = createSignal<string>("");

  const [dialog, setDialog] = createSignal<DialogState>({
    isOpen: false,
    mode: "create",
    targetVnc: null,
    inputValue: "",
    urlValue: DEFAULT_VNC_URL,
  });

  onMount(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setVncs(JSON.parse(stored) as VncPanel[]);
      } catch (e) {
        setVncs([]);
      }
    } else {
      setVncs([
        {
          id: `vnc-${Date.now()}`,
          name: "Example Vnc Panel 1",
          params: {
            url: DEFAULT_VNC_URL,
          },
        },
      ]);
    }
  });

  createEffect(() => {
    if (vncs().length > 0 || localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(vncs()));
    }
  });

  const filteredVncs = () =>
    vncs().filter((v) =>
      v.name.toLowerCase().includes(searchQuery().toLowerCase()),
    );

  const handleOpenVnc = (vnc: VncPanel) => {
    openInCentral({
      id: `vnc-${vnc.id}`,
      title: vnc.name,
      elementTag: "vnc-viewer",
      params: {
        url: vnc.params.url,
      },
    });
  };

  const openCreateDialog = () => {
    setDialog({
      isOpen: true,
      mode: "create",
      targetVnc: null,
      inputValue: "",
      urlValue: DEFAULT_VNC_URL,
    });
  };

  const openEditDialog = (vnc: VncPanel, e: MouseEvent) => {
    e.stopPropagation();
    setDialog({
      isOpen: true,
      mode: "edit",
      targetVnc: vnc,
      inputValue: vnc.name,
      urlValue: vnc.params.url,
    });
  };

  const openDeleteDialog = (vnc: VncPanel, e: MouseEvent) => {
    e.stopPropagation();
    setDialog({
      isOpen: true,
      mode: "delete",
      targetVnc: vnc,
      inputValue: "",
      urlValue: "",
    });
  };

  const handleDialogSubmit = () => {
    const { mode, targetVnc, inputValue, urlValue } = dialog();
    const trimmedInput = inputValue.trim();
    const trimmedUrl = urlValue.trim() || DEFAULT_VNC_URL;

    if (mode === "create") {
      if (!trimmedInput) return;
      const newVnc: VncPanel = {
        id: `vnc-${Date.now()}`,
        name: trimmedInput,
        params: {
          url: trimmedUrl,
        },
      };
      setVncs((prev) => [newVnc, ...prev]);
      handleOpenVnc(newVnc);
    } else if (mode === "edit" && targetVnc) {
      if (
        !trimmedInput ||
        (trimmedInput === targetVnc.name && trimmedUrl === targetVnc.params.url)
      ) {
        setDialog((prev) => ({ ...prev, isOpen: false }));
        return;
      }
      const updatedVnc: VncPanel = {
        id: targetVnc.id,
        name: trimmedInput,
        params: {
          url: trimmedUrl,
        },
      };
      setVncs((prev) =>
        prev.map((v) => (v.id === targetVnc.id ? updatedVnc : v)),
      );
      handleOpenVnc(updatedVnc);
    } else if (mode === "delete" && targetVnc) {
      setVncs((prev) => prev.filter((v) => v.id !== targetVnc.id));
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
            title="New VNC panel"
          >
            <FiPlus class="size-4" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-bg">
          <Show
            when={filteredVncs().length > 0}
            fallback={
              <div class="p-4 text-center text-sm text-fg opacity-50 italic">
                No VNC panels found.
              </div>
            }
          >
            <For each={filteredVncs()}>
              {(vnc) => (
                <div
                  class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
                  onClick={() => handleOpenVnc(vnc)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") handleOpenVnc(vnc);
                  }}
                >
                  <div class="flex items-center gap-3 truncate">
                    <div class="text-icons group-hover:text-links transition-colors shrink-0">
                      <TbDeviceDesktop class="size-4" />
                    </div>
                    <div class="flex flex-col truncate">
                      <span class="font-medium text-sm text-fg truncate">
                        {vnc.name}
                      </span>
                      <span class="text-[10px] text-fg opacity-50 truncate font-mono mt-0.5">
                        Url: {vnc.params.url}
                      </span>
                    </div>
                  </div>

                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => openEditDialog(vnc, e)}
                      class="p-1.5 hover:bg-icon-btn-bg-hover hover:text-links rounded text-icons transition-colors"
                      title="Edit"
                    >
                      <FiEdit2 class="size-3.5" />
                    </button>
                    <button
                      onClick={(e) => openDeleteDialog(vnc, e)}
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
                  {dialog().mode === "create" && "Create New VNC panel"}
                  {dialog().mode === "edit" && "Edit VNC panel"}
                  {dialog().mode === "delete" && "Delete VNC panel"}
                </Dialog.Title>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>

              <Dialog.Description class="mb-5 text-sm opacity-80">
                {dialog().mode === "delete"
                  ? `Are you sure you want to delete "${dialog().targetVnc?.name}"? This action cannot be undone.`
                  : "Please enter a name and url for your VNC panel."}
              </Dialog.Description>

              <Show when={dialog().mode !== "delete"}>
                <input
                  type="text"
                  value={dialog().inputValue}
                  onInput={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      inputValue: e.currentTarget.value,
                    }))
                  }
                  placeholder="VNC panel name..."
                  autofocus
                  class="w-full px-3 py-2 mb-3 text-sm bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded-md text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] focus:ring-1 focus:ring-[var(--links)] transition-all"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleDialogSubmit();
                  }}
                />
                <input
                  type="text"
                  value={dialog().urlValue}
                  onInput={(e) =>
                    setDialog((prev) => ({
                      ...prev,
                      urlValue: e.currentTarget.value,
                    }))
                  }
                  placeholder="VNC URL..."
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
