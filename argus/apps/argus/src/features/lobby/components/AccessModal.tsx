/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Mode } from "@/services/app-mode";
import { Show } from "solid-js";
import { createEffect } from "solid-js";

type AccessModalProps = {
  open: boolean;
  mode: Mode | null;
  accessKey: string;
  onAccessKeyChange: (value: string) => void;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
  error: string | null;
};

export function AccessModal(props: AccessModalProps) {
  let inputRef: HTMLInputElement | undefined;

  createEffect(() => {
    if (!props.open) return;

    queueMicrotask(() => {
      inputRef?.focus();
    });
  });

  const okAction = () => {
   props.onConfirm();
  }

  return (
    <Show when={props.open}>
      <div class="fixed inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm">
        <div class="bg-white shadow-lg w-64 p-4 flex flex-col gap-3">
          <span class="text-sm font-semibold text-gray-800">
            {props.mode === Mode.GameMaster ? "GM Access" : "SCADA Access"}
          </span>

          <input
            ref={inputRef}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                okAction();
              }
              if (e.key === "Escape") {
                props.onCancel();
              }
            }}
            placeholder="Access key"
            class="border border-gray-300 rounded px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            value={props.accessKey}
            aria-invalid={props.error !== null}
            onInput={(e) => props.onAccessKeyChange(e.currentTarget.value)}
          />

          <Show when={props.error}>
            {(message) => (
              <p class="border-l-2 border-red-600 bg-red-50 px-2 py-1 text-xs text-red-800">
                {message()}
              </p>
            )}
          </Show>

          <div class="flex justify-end gap-2">
            <button
              class="bg-gray-200 px-3 py-1 text-xs enabled:hover:bg-gray-300 disabled:opacity-50"
              onClick={props.onCancel}
            >
              Cancel
            </button>

            <button
              class="px-3 py-1 bg-slate-800 hover:bg-cyan-600 text-white font-mono text-xs font-bold uppercase tracking-wider transition-colors"
              onClick={okAction}
            >
              OK
            </button>
          </div>
        </div>
      </div>
    </Show>
  );
}
