/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, For, Show, type Component } from "solid-js";
import { Dialog } from "@kobalte/core/dialog";
import { FiX, FiCheck } from "solid-icons/fi";
import { PendingEdit } from "../types";
import { backendPost } from "@/services/backend/service";
import { toControlKind } from "../columnMapping";

interface ControlResult {
  edit: PendingEdit;
  status: "pending" | "success" | "error";
  message?: string;
}

interface ScadaControlPopupProps {
  open: boolean;
  onClose: () => void;
  edits: PendingEdit[];
  requester: string;
  onSuccess: (successfulPendingEdits: PendingEdit[]) => void;
}

export const ScadaControlPopup: Component<ScadaControlPopupProps> = (props) => {
  const [results, setResults] = createSignal<ControlResult[]>(
    props.edits.map((edit) => ({ edit, status: "pending" }))
  );
  const [sent, setSent] = createSignal(false);

  const sendAll = async () => {
    const updated = [...results()];
    const successfulPendingEdits: PendingEdit[] = [];
    for (let i = 0; i < updated.length; i++) {
      const { edit } = updated[i];
      try {
        await backendPost(
          `/control/${encodeURIComponent(edit.rowId)}/${toControlKind(edit.column)}/${edit.newValue}?requester=${encodeURIComponent(props.requester)}`,
          {}
        );
        updated[i] = { ...updated[i], status: "success" };
        successfulPendingEdits.push(edit);
      } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        updated[i] = { ...updated[i], status: "error", message };
      }
      setResults([...updated]);
    }
    props.onSuccess(successfulPendingEdits);
    setSent(true);
  };

  return (
    <Dialog open={props.open} onOpenChange={(o) => { if (!o) props.onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
        <div class="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
          <Dialog.Content class="pointer-events-auto w-full max-w-md rounded-lg bg-[var(--popover-bg)] p-6 text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none">
            <div class="flex items-center justify-between mb-4">
              <Dialog.Title class="text-lg font-medium text-[var(--title-color)]">Send Controls</Dialog.Title>
              <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                <FiX class="size-4" />
              </Dialog.CloseButton>
            </div>

            <div class="rounded border border-[var(--border)] divide-y divide-[var(--border)] mb-5 max-h-64 overflow-y-auto custom-scrollbar">
              <For each={results()}>
                {(result) => (
                  <div class="flex items-center justify-between px-3 py-2 text-sm">
                    <div class="flex flex-col truncate">
                      <span class="font-mono text-xs text-[var(--code-text)] truncate">{result.edit.rowId}</span>
                      <span class="text-[10px] opacity-50">{result.edit.column} → {String(result.edit.newValue)}</span>
                    </div>
                    <div class="shrink-0 ml-2">
                      <Show when={result.status === "pending"}>
                        <span class="text-xs opacity-40">—</span>
                      </Show>
                      <Show when={result.status === "success"}>
                        <FiCheck class="size-4 text-[var(--success-color)]" />
                      </Show>
                      <Show when={result.status === "error"}>
                        <div class="flex flex-col items-end gap-0.5">
                          <span class="text-xs text-[var(--warning-icon)]">✕</span>
                          <Show when={result.message}>
                            <span class="text-[10px] text-[var(--warning-icon)] opacity-80 max-w-[200px] text-right">{result.message}</span>
                          </Show>
                        </div>
                      </Show>
                    </div>
                  </div>
                )}
              </For>
            </div>

            <div class="flex justify-end gap-3">
              <button onClick={props.onClose} class="px-4 py-2 text-sm font-medium rounded-md border border-[var(--border)] bg-[var(--search-btn-bg)] hover:bg-[var(--theme-hover)] transition-colors">
                Close
              </button>
              <Show when={!sent()}>
                <button onClick={sendAll} class="px-4 py-2 text-sm font-medium rounded-md bg-[var(--links)] text-white hover:opacity-90 transition-all">
                  Send
                </button>
              </Show>
            </div>
          </Dialog.Content>
        </div>
      </Dialog.Portal>
    </Dialog>
  );
};
