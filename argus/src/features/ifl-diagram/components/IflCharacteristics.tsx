/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, createSignal, For, Show } from "solid-js";
import { FunctionEditor } from "./FunctionEditor";
import { PickInfo } from "../types";
import { backendGet, backendPost } from "@/services/backend";

const REQUESTER = "argus";

interface Characteristics {
  delay_function?: Record<string, unknown>;
  drop_function?: Record<string, unknown>;
  corruption_functions?: Record<string, unknown>[];
}

interface Props {
  selected: PickInfo;
  readOnly: boolean;
}

export const IflCharacteristics: Component<Props> = (props) => {
  const [loading, setLoading] = createSignal(true);
  const [error, setError] = createSignal<string | null>(null);
  const [saving, setSaving] = createSignal(false);

  // Editable state
  const [delayParams, setDelayParams] = createSignal<Record<string, unknown> | null>(null);
  const [dropParams, setDropParams] = createSignal<Record<string, unknown> | null>(null);
  const [corruptionParams, setCorruptionParams] = createSignal<Record<string, unknown>[]>([]);
  const [valid, setValid] = createSignal(true);

  const getUrl = () => {
    const sel = props.selected;
    if (sel.elementType === "node")
      return `/get-node-characteristics?node=${encodeURIComponent(sel.nodeId)}&requester=${REQUESTER}`;
    return `/get-link-characteristics?from=${encodeURIComponent(sel.from)}&to=${encodeURIComponent(sel.to)}&requester=${REQUESTER}`;
  };

  const setUrl = () => {
    const sel = props.selected;
    if (sel.elementType === "node")
      return `/set-node-characteristics?node=${encodeURIComponent(sel.nodeId)}&requester=${REQUESTER}`;
    return `/set-link-characteristics?from=${encodeURIComponent(sel.from)}&to=${encodeURIComponent(sel.to)}&requester=${REQUESTER}`;
  };

  (async () => {
    try {
      const data = await backendGet<Characteristics>(getUrl()).catch((e) => {
        throw new Error(`Failed to fetch characteristics: ${e}`);
      });
      const nonEmpty = (o?: Record<string, unknown>) =>
        o && Object.keys(o).length > 0 ? o : null;
      setDelayParams(nonEmpty(data.delay_function));
      setDropParams(nonEmpty(data.drop_function));
      setCorruptionParams(
        (data.corruption_functions ?? []).filter((c) => Object.keys(c).length > 0)
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  })();

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const body = {
        delay_function: delayParams() ?? {},
        drop_function: dropParams() ?? {},
        corruption_functions: corruptionParams(),
      };

      await backendPost(setUrl(), body).catch((e) => {
        throw new Error(`Failed to save characteristics: ${e}`);
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div class="mt-3 pt-3 border-t border-border space-y-3">
      <Show when={loading()}>
        <p class="text-xs text-text-muted">Loading characteristics…</p>
      </Show>
      <Show when={error()}>
        <p class="text-xs text-red-500">{error()}</p>
      </Show>
      <Show when={!loading()}>
        <FunctionEditor
          functionClass="delay_function"
          initParams={delayParams() ?? undefined}
          readOnly={props.readOnly}
          onChange={(p, v) => { setDelayParams(p); setValid(v); }}
        />
        <FunctionEditor
          functionClass="drop_function"
          initParams={dropParams() ?? undefined}
          readOnly={props.readOnly}
          onChange={(p, v) => { setDropParams(p); setValid(v); }}
        />

        <div class="space-y-2">
          <span class="text-xs text-text-muted">Corruption functions</span>
          <For each={corruptionParams()}>
            {(cp, i) => (
              <div class="pl-2 border-l border-border">
                <FunctionEditor
                  functionClass="corruption_function"
                  initParams={cp}
                  readOnly={props.readOnly}
                  onChange={(p) =>
                    setCorruptionParams((prev) =>
                      prev.map((x, j) => j === i() ? p : x).filter(Boolean) as Record<string, unknown>[]
                    )
                  }
                />
                <Show when={!props.readOnly}>
                  <button
                    class="text-xs text-red-400 hover:text-red-600 mt-1"
                    onClick={() => setCorruptionParams((prev) => prev.filter((_, j) => j !== i()))}
                  >
                    Remove
                  </button>
                </Show>
              </div>
            )}
          </For>
          <Show when={!props.readOnly}>
            <button
              class="text-xs text-accent hover:text-accent-hover"
              onClick={() => setCorruptionParams((prev) => [...prev, {}])}
            >
              + Add corruption
            </button>
          </Show>
        </div>

        <Show when={!props.readOnly}>
          <button
            class="w-full text-xs bg-accent text-text-on-accent rounded px-3 py-1.5 hover:bg-accent-hover disabled:opacity-50"
            disabled={!valid() || saving()}
            onClick={save}
          >
            {saving() ? "Saving…" : "Save"}
          </button>
        </Show>
      </Show>
    </div>
  );
};
