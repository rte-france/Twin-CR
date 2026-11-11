/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { AccessKeyTyped } from "@/services/session-manager/types";
import { For, Show, createEffect, createResource, createSignal, onMount, onCleanup } from "solid-js";
import { createStore } from "solid-js/store";
import { Icon } from "@iconify-icon/solid";
import { getAccessKeys, parseUtcDate, setAccessKeys } from "@/services/session-manager";

const pad = (value: number) => String(value).padStart(2, "0");

const utcToLocalInput = (utc: string) => {
  const at = parseUtcDate(utc);
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}` +
    `T${pad(at.getHours())}:${pad(at.getMinutes())}`;
};

const localInputToUtc = (local: string) => {
  const at = new Date(local);
  return Number.isNaN(at.getTime()) ? null : at.toISOString().replace("Z", "");
};
const dateToUtc = (d: Date) => {
  return Number.isNaN(d.getTime()) ? null : d.toISOString().replace("Z", "");
};

type Props = {
  sessionId: number;
  sessionName: string;
  onClose: () => void;
};

export function AccessKeysModal(props: Props) {
  const [keys, setKeys] = createStore<AccessKeyTyped[]>([]);
  const [copiedId, setCopiedId] = createSignal<number | null>(null);
  const [fetchedKeys] = createResource(() => props.sessionId, getAccessKeys);

  const openedAt = new Date();

  const isOutdated = (validityLimit: string | null | undefined) => {
    if (!validityLimit) return false;
    return openedAt > new Date(validityLimit);
  };

  onMount(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        props.onClose();
      }
    };
    window.addEventListener("keydown", handler);
    onCleanup(() => window.removeEventListener("keydown", handler));
  });

  createEffect(() => {
    if (fetchedKeys.error) {
      console.error("Could not load access keys:", fetchedKeys.error);
      return;
    }
    const access_keys = fetchedKeys();
    if (access_keys) {
      setKeys(access_keys);
    }
  });

  const copyPassword = async (password: string, id: number) => {
    await navigator.clipboard.writeText(password);

    setCopiedId(id);

    setTimeout(() => {
      if (copiedId() === id) {
        setCopiedId(null);
      }
    }, 900);
  };

  const updateKey = async (
    index: number,
    field: keyof AccessKeyTyped,
    value: string | boolean
  ) => {
    setKeys(index, field as any, value as any);

    const updatedKey = {
      ...keys[index],
      [field]: value,
    };

    await setAccessKeys(updatedKey);
  };

  const roleLabels: Record<string, string> = {
    GM: "Game master key",
    OP: "Operator key",
    GK: "Golden key",
  };

  return (
    <div class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50">
      <div class="w-[1000px] max-h-[85vh] overflow-y-auto bg-white p-6 shadow-xl">
        <h2 class="mb-4 text-lg font-semibold">Access keys - {props.sessionName}</h2>

        <div class="grid grid-cols-3 gap-4">
          <For each={keys}>
            {(key, index) => (
              <div class="border border-slate-300 bg-white overflow-hidden">
                <div class="px-4 py-2 bg-slate-900 border-b border-cyan-600 flex justify-between items-center">
                  <h3 class="font-mono text-xs font-bold uppercase tracking-[0.25em] text-slate-300">
                    {roleLabels[key.type.toUpperCase()]}
                  </h3>

                  <span
                    class={`px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${
                      key.revoked
                        ? "bg-red-100 text-red-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {key.revoked ? "Revoked" : "Active"}
                  </span>
                </div>

                <div class="p-4">
                    <div class="flex flex-col items-center mb-4">
                      <div class="mb-2 font-mono text-[11px] uppercase tracking-wider text-slate-500">
                        Access Key
                      </div>

                      <div class="px-4 py-3">
                        <div class="font-mono text-3xl font-bold tracking-wider text-slate-500">
                          {key.password}
                        </div>
                      </div>

                      <div class="mt-2">
                        <button
                          class="flex items-center gap-2 px-3 py-1.5 bg-slate-600 hover:bg-cyan-600 text-white text-xs font-mono uppercase tracking-wider transition-colors"
                          onClick={async () => copyPassword(key.password, key.id)}
                        >
                          <Show
                            when={copiedId() !== key.id}
                            fallback={<Icon icon="lucide:check" />}
                          >
                            <Icon icon="lucide:copy" />
                          </Show>

                          {copiedId() === key.id ? "Copied" : "Copy"}
                        </button>
                      </div>
                    </div>

                    <div class="mb-4">
                      <label class="mb-1 block font-mono text-[11px] uppercase tracking-wider text-slate-500">
                        Valid Until
                      </label>

                      <div class="flex gap-2">
                        <input
                          type="datetime-local"
                          class="flex-1 border border-slate-300 bg-white px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
                          value={utcToLocalInput(key.validity_limit)}
                          onInput={(e) => {
                            const utc = localInputToUtc(e.currentTarget.value);
                            if (utc) {
                              updateKey(index(), "validity_limit", utc);
                            }
                          }}
                        />

                        <Show when={isOutdated(key.validity_limit)}>
                          <button
                            type="button"
                            class="px-3 py-2 bg-slate-600 hover:bg-cyan-600 text-white transition-colors"
                          onClick={() => {
                            const renewedDate = new Date();
                            renewedDate.setHours(renewedDate.getHours() + 24);
                            const utc = dateToUtc(renewedDate);
                            if (utc) {
                              updateKey(index(), "validity_limit", utc);
                            }
                          }}
                            title="Renew key for 24 hours"
                          >
                            <Icon icon="lucide:refresh-cw" />
                          </button>
                        </Show>
                      </div>

                      <Show when={isOutdated(key.validity_limit)}>
                        <div class="mt-1 text-xs text-red-500">
                          Outdated
                        </div>
                      </Show>
                    </div>

                    <div class="mb-4">
                      <label class="mb-1 block font-mono text-[11px] uppercase tracking-wider text-slate-500">
                        Usage Policy
                      </label>

                      <select
                        class="w-full border border-slate-300 bg-white px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
                        value={key.usage}
                        onChange={(e) =>
                          updateKey(
                            index(),
                            "usage",
                            e.currentTarget.value
                          )
                        }
                      >
                        <option value="unique">Single Use</option>
                        <option value="multi">Multi Use</option>
                      </select>
                    </div>

                    <label class="flex items-center gap-3 border-t border-slate-200 pt-3">
                      <input
                        type="checkbox"
                        checked={key.revoked}
                        onChange={(e) =>
                          updateKey(
                            index(),
                            "revoked",
                            e.currentTarget.checked
                          )
                        }
                      />

                      <span class="font-mono text-[11px] uppercase tracking-wider text-slate-600">
                        Revoke Credential
                      </span>
                    </label>
                </div>
              </div>
            )}
          </For>
        </div>

        <hr class="my-4 border-slate-300" />

        <div class="flex justify-end">
          <button
            class="px-4 py-2 bg-slate-800 hover:bg-cyan-600 text-white font-mono text-xs uppercase tracking-wider transition-colors"
            onClick={props.onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
