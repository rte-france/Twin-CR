/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, For, Show } from "solid-js";
import {
  FiX,
  FiTrash2,
  FiPlay,
  FiSearch,
  FiEdit2,
  FiCheck,
  FiAlertCircle,
} from "solid-icons/fi";
import { FaSolidSpinner } from "solid-icons/fa";
import { useTimeline } from "../context/TimelineContext";

export function WhenEventsDrawer() {
  const {
    whenEvents,
    deleteEvent,
    addEvent,
    editEvent,
    leftDrawerOpen,
    setLeftDrawerOpen,
  } = useTimeline();
  const [searchQuery, setSearchQuery] = createSignal("");

  const [editingId, setEditingId] = createSignal<string | null>(null);
  const [editText, setEditText] = createSignal("");
  const [savingId, setSavingId] = createSignal<string | null>(null);
  const [editError, setEditError] = createSignal<string | null>(null);

  const startEditing = (id: string, action: string) => {
    setEditingId(id);
    setEditText(action);
    setEditError(null);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditError(null);
  };

  const saveEditing = (id: string) => {
    if (savingId()) return;
    setSavingId(id);
    editEvent(id, editText())
      .then(() => {
        setSavingId(null);
        setEditingId(null);
      })
      .catch((err: Error) => {
        setSavingId(null);
        setEditError(err.message);
      });
  };

  const filteredEvents = () => {
    const query = searchQuery().toLowerCase().trim();
    if (!query) return whenEvents();
    return whenEvents().filter(
      (e) =>
        e.id.toLowerCase().includes(query) ||
        e.action.toLowerCase().includes(query) ||
        (e.source && e.source.toLowerCase().includes(query)),
    );
  };

  return (
    <div
      class="bg-[var(--sidebar-bg)] border-r border-[var(--border)] flex flex-col shrink-0 relative transition-all duration-300 ease-in-out z-40"
      style={{
        width: leftDrawerOpen() ? "380px" : "0px",
        opacity: leftDrawerOpen() ? "1" : "0",
        "pointer-events": leftDrawerOpen() ? "auto" : "none",
      }}
    >
      {/* Header Interne */}
      <header class="h-9 px-3 flex items-center justify-between border-b border-[var(--border-light)] bg-[var(--bg)]/30 shrink-0 select-none">
        <span class="text-[10px] font-bold uppercase tracking-wider text-[var(--icons)]">
          When Conditions ({whenEvents().length})
        </span>
        <button
          type="button"
          onClick={() => setLeftDrawerOpen(false)}
          class="p-1 rounded-sm text-[var(--icons)] hover:bg-[var(--warning-bg)] hover:text-[var(--warning-icon)] transition-colors"
        >
          <FiX class="size-3.5" />
        </button>
      </header>

      {/* Barre de Recherche Compacte */}
      <div class="p-2 border-b border-[var(--border-light)]/60 bg-[var(--bg)]/10 shrink-0">
        <div class="relative flex items-center h-6">
          <FiSearch class="absolute left-2 size-3 text-[var(--icons)]/60" />
          <input
            type="text"
            placeholder="Filter conditions..."
            value={searchQuery()}
            onInput={(e) => setSearchQuery(e.currentTarget.value)}
            class="w-full h-full pl-7 pr-2 bg-[var(--pre-bg)] border border-[var(--border-light)] rounded-[3px] text-[10px] font-sans text-[var(--fg)] outline-none focus:border-[var(--links)] transition-all"
          />
        </div>
      </div>

      <Show when={editError()}>
        <div class="flex items-center gap-1.5 px-2 py-1.5 border-b border-[var(--warning-border)] bg-[var(--warning-bg)] text-[var(--warning-icon)] text-[10px] shrink-0">
          <FiAlertCircle class="size-3 shrink-0" />
          <span class="break-all">{editError()}</span>
        </div>
      </Show>

      {/* Liste Virtuelle/Dense sous forme de Tableur vertical */}
      <div class="flex-1 overflow-auto scrollbar-thin bg-[var(--bg)]/5">
        <div class="min-w-[378px] h-full flex flex-col">
          <table class="w-full text-left border-collapse font-sans text-[11px]">
            <thead class="sticky top-0 bg-[var(--sidebar-bg)] border-b border-[var(--border-light)] text-[8px] uppercase tracking-wider text-[var(--icons)] font-bold z-10">
              <tr>
                <th class="p-2 pl-3 w-[25%]">Source</th>
                <th class="p-2 w-[55%]">DSL Action</th>
                <th class="p-2 pr-3 w-[20%] text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--border-light)]/30 font-mono">
              <For
                each={filteredEvents()}
                fallback={
                  <tr>
                    <td
                      colspan="3"
                      class="p-8 text-center font-sans text-[11px] text-[var(--icons)] opacity-60"
                    >
                      No matching conditions found.
                    </td>
                  </tr>
                }
              >
                {(ev) => (
                  <tr class="hover:bg-[var(--theme-hover)]/30 group transition-colors align-top">
                    {/* Source / Condition */}
                    <td class="p-2 pl-3 text-[var(--warning-icon)] font-bold break-all whitespace-pre-wrap leading-tight text-[10px]">
                      {ev.source || "N/A"}
                    </td>
                    {/* Commande */}
                    <td class="p-2 text-[var(--code-text)] text-[10px] break-all whitespace-pre-wrap leading-normal">
                      <Show
                        when={editingId() === ev.id}
                        fallback={<span title={ev.action}>{ev.action}</span>}
                      >
                        <textarea
                          value={editText()}
                          onInput={(e) => setEditText(e.currentTarget.value)}
                          disabled={savingId() === ev.id}
                          rows={3}
                          class="w-full bg-[var(--pre-bg)] border border-[var(--links)] rounded-[3px] p-1 text-[10px] font-mono text-[var(--code-text)] outline-none resize-none disabled:opacity-70"
                        />
                      </Show>
                    </td>
                    {/* Boutons d'action rapides */}
                    <td class="p-2 pr-3 text-right font-sans opacity-40 group-hover:opacity-100 transition-opacity">
                      <Show
                        when={editingId() === ev.id}
                        fallback={
                          <div class="flex items-center justify-end gap-1">
                            <Show when={ev.status === "ready"}>
                              <button
                                type="button"
                                onClick={() => startEditing(ev.id, ev.action)}
                                class="p-1 rounded-[2px] text-[var(--fg)] hover:bg-[var(--theme-hover)]"
                                title="Edit (Ready events only)"
                              >
                                <FiEdit2 class="size-3" />
                              </button>
                            </Show>
                            <button
                              type="button"
                              onClick={() => addEvent(ev.action)}
                              class="p-1 rounded-[2px] text-[var(--success-color)] hover:bg-[var(--success-color)]/10"
                              title="Force Trigger"
                            >
                              <FiPlay class="size-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => deleteEvent(ev.id)}
                              class="p-1 rounded-[2px] text-[var(--warning-icon)] hover:bg-[var(--warning-bg)]"
                            >
                              <FiTrash2 class="size-3" />
                            </button>
                          </div>
                        }
                      >
                        <div class="flex items-center justify-end gap-1 opacity-100">
                          <button
                            type="button"
                            onClick={cancelEditing}
                            disabled={savingId() === ev.id}
                            class="px-1.5 py-0.5 rounded-[2px] text-[9px] text-[var(--fg)] hover:bg-[var(--theme-hover)] disabled:opacity-50"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => saveEditing(ev.id)}
                            disabled={savingId() === ev.id}
                            class="p-1 rounded-[2px] text-[var(--success-color)] hover:bg-[var(--success-color)]/10 disabled:opacity-50"
                          >
                            <Show
                              when={savingId() !== ev.id}
                              fallback={<FaSolidSpinner class="size-3 animate-spin" />}
                            >
                              <FiCheck class="size-3" />
                            </Show>
                          </button>
                        </div>
                      </Show>
                    </td>
                  </tr>
                )}
              </For>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
