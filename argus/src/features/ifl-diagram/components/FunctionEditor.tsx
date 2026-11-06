/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, createSignal, For, Show } from "solid-js";
import { schema, FunctionEntry } from "../types/functionsSchema";

interface Props {
  functionClass: "delay_function" | "drop_function" | "corruption_function";
  initParams?: Record<string, unknown>;
  readOnly: boolean;
  onChange?: (params: Record<string, unknown> | null, valid: boolean) => void;
}

function makeDefaultParams(entry: FunctionEntry): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(entry.parameters).map(([key, info]) => [
      key,
      info.default !== undefined ? info.default : info.type === "bool" ? false : "",
    ])
  );
}

function validate(entry: FunctionEntry, values: Record<string, unknown>) {
  const errors: Record<string, string> = {};
  const coerced = { ...values };
  for (const [key, info] of Object.entries(entry.parameters)) {
    const val = values[key];
    if (info.type === "double") {
      if (val === "" || isNaN(Number(val))) errors[key] = "Must be a number";
      else coerced[key] = Number(val);
    }
    if (info.type === "bool" && val !== true && val !== false) {
      errors[key] = "Must be true or false";
    }
  }
  return { errors, coerced };
}

export const FunctionEditor: Component<Props> = (props) => {
  const entry = () => schema[props.functionClass];
  const functionTypes = () => Object.keys(entry());

  const [type, setType] = createSignal(props.initParams?.type as string ?? "");
  const [params, setParams] = createSignal<Record<string, unknown>>(props.initParams ?? {});
  const [errors, setErrors] = createSignal<Record<string, string>>({});

  const label = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

  function notify(t: string, p: Record<string, unknown>) {
    if (!props.onChange) return;
    if (!t) { props.onChange(null, true); return; }
    const { errors, coerced } = validate(entry()[t], p);
    setErrors(errors);
    props.onChange({ ...coerced, type: t }, Object.keys(errors).length === 0);
  }

  function handleTypeChange(t: string) {
    setType(t);
    if (!t) {
      setParams({});
      setErrors({});
      notify("", {});
      return;
    }
    const defaults = makeDefaultParams(entry()[t]);
    // Keep existing values for matching keys
    const next: Record<string, unknown> = {};
    const prev = params();
    for (const key of Object.keys(defaults)) {
      next[key] = key in prev ? prev[key] : defaults[key];
    }
    setParams(next);
    notify(t, next);
  }

  function handleParamChange(key: string, value: unknown) {
    const next = { ...params(), [key]: value };
    setParams(next);
    notify(type(), next);
  }

  return (
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <span class="w-1/3 text-xs text-text-muted">{label(props.functionClass)}</span>
        <Show
          when={!props.readOnly}
          fallback={<span class="w-1/3 text-xs font-medium">{type() || "—"}</span>}
        >
          <select
            class="w-2/3 text-xs bg-surface border border-border rounded px-2 py-1"
            value={type()}
            onChange={(e) => handleTypeChange(e.currentTarget.value)}
          >
            <option value="">(none)</option>
            <For each={functionTypes()}>
              {(t) => <option value={t}>{t}</option>}
            </For>
          </select>
        </Show>
      </div>

      <Show when={type()}>
        <For each={Object.entries(entry()[type()].parameters)}>
          {([key, info]) => {
            const val = () => params()[key] ?? (info.type === "bool" ? false : "");
            const hasError = () => key in errors();
            return (
              <div class="flex items-center gap-2 pl-2">
                <span class="w-1/3 text-xs text-text-muted">{label(key)}</span>
                <Show
                  when={!props.readOnly}
                  fallback={<span class="w-1/3 text-xs font-medium">{String(val())}</span>}
                >
                  <Show
                    when={info.type === "bool"}
                    fallback={
                      <input
                        class="w-2/3 text-xs px-2 py-1 rounded border"
                        classList={{
                          "border-border bg-surface": !hasError(),
                          "border-red-500 bg-red-50": hasError(),
                        }}
                        value={val() as string}
                        onChange={(e) => handleParamChange(key, e.currentTarget.value)}
                      />
                    }
                  >
                    <input
                      type="checkbox"
                      checked={val() as boolean}
                      disabled={props.readOnly}
                      onChange={(e) => handleParamChange(key, e.currentTarget.checked)}
                    />
                  </Show>
                </Show>
              </div>
            );
          }}
        </For>
      </Show>
    </div>
  );
};
