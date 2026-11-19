/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, Switch, Match, createSignal, For } from "solid-js";
import { FiCheck, FiPlus, FiX } from "solid-icons/fi";
import type { SettingFieldDefinition } from "../types";

export function SettingItem(props: {
  field: SettingFieldDefinition;
  sectionId: string;
  value: any;
  isSaving: boolean;
  onUpdate: (val: any) => Promise<void>;
  onReset?: () => Promise<void>;
}) {
  const [success, setSuccess] = createSignal(false);
  const [localText, setLocalText] = createSignal<string | null>(null);
  const [newTagInput, setNewTagInput] = createSignal("");

  const displayVal = () => {
    if (localText() !== null) return localText()!;
    if (props.value === undefined || props.value === null) {
      if (props.field.defaultValue !== undefined) return props.field.defaultValue;
      return props.field.type === "string[]" ? [] : "";
    }
    return props.value;
  };

  const currentArray = (): string[] => {
    const val = props.value ?? props.field.defaultValue;
    if (Array.isArray(val)) return val;
    if (typeof val === "string" && val.trim().length > 0) return [val];
    return [];
  };

  const triggerSuccess = () => {
    setSuccess(true);
    setTimeout(() => setSuccess(false), 1500);
  };

  const handleTextCommit = async () => {
    if (localText() === null) return;
    const raw = localText()!;
    setLocalText(null);

    let parsedVal: any = raw;
    if (props.field.type === "number") {
      parsedVal = raw === "" ? null : Number(raw);
    } else if (props.field.type === "string") {
      parsedVal = raw.trim() === "" ? null : raw;
    }

    try {
      await props.onUpdate(parsedVal);
      triggerSuccess();
    } catch {
      // Revert handled by reactive state
    }
  };

  const handleAddTag = async () => {
    const item = newTagInput().trim();
    if (!item) return;
    const current = currentArray();
    if (current.includes(item)) {
      setNewTagInput("");
      return;
    }
    const next = [...current, item];
    setNewTagInput("");
    await props.onUpdate(next);
    triggerSuccess();
  };

  const handleRemoveTag = async (indexToRemove: number) => {
    const next = currentArray().filter((_, i) => i !== indexToRemove);
    await props.onUpdate(next);
    triggerSuccess();
  };

  const isWideLayout = () => props.field.type === "string[]";

  return (
    <div
      class={`border-b border-divider hover:bg-[var(--media-bg)]/30 transition-colors py-3.5 px-4 group ${
        isWideLayout()
          ? "flex flex-col gap-2.5"
          : "flex items-start justify-between gap-6"
      }`}
    >
      {/* Label and description */}
      <div class="flex-1 min-w-0 flex flex-col gap-0.5">
        <div class="flex items-center gap-2">
          <span class="text-[13px] font-medium text-[var(--fg)] tracking-tight">
            {props.field.label}
          </span>
          <span class="text-[10px] font-mono text-[var(--sidebar-non-existant)] opacity-70">
            {props.sectionId === "network"
              ? props.field.key
              : `${props.sectionId}.${props.field.key}`}
          </span>
          <Show when={props.isSaving}>
            <span class="text-[10px] text-[var(--sidebar-non-existant)] animate-pulse font-mono ml-1">
              saving...
            </span>
          </Show>
          <Show when={success()}>
            <span class="text-[var(--success-color,#10b981)] animate-in fade-in ml-1">
              <FiCheck class="w-3.5 h-3.5 inline" />
            </span>
          </Show>
        </div>
        <p class="text-[12px] text-[var(--sidebar-fg)] opacity-80 leading-relaxed max-w-2xl">
          {props.field.description}
        </p>
      </div>

      {/* Control element */}
      <div class={isWideLayout() ? "w-full max-w-2xl pt-1" : "shrink-0 pt-0.5"}>
        <Switch>
          {/* Boolean switch */}
          <Match when={props.field.type === "boolean"}>
            <button
              type="button"
              disabled={props.isSaving}
              onClick={async () => {
                const currentBool = Boolean(displayVal());
                await props.onUpdate(!currentBool);
                triggerSuccess();
              }}
              class={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                Boolean(displayVal())
                  ? "bg-[var(--sidebar-active)]"
                  : "bg-[var(--border)] hover:bg-[var(--border-hover)]"
              }`}
            >
              <span
                class={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                  Boolean(displayVal()) ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </button>
          </Match>

          {/* Select dropdown */}
          <Match when={props.field.type === "select"}>
            <select
              value={String(displayVal())}
              disabled={props.isSaving}
              onChange={async (e) => {
                await props.onUpdate(e.currentTarget.value);
                triggerSuccess();
              }}
              class="bg-[var(--bg)] border border-[var(--border)] text-[var(--fg)] rounded px-3 py-1.5 text-xs focus:outline-none focus:border-[var(--sidebar-active)] shadow-sm font-sans cursor-pointer hover:border-[var(--border-hover)] min-w-[140px]"
            >
              <Show when={props.field.options}>
                {(options) =>
                  options().map((opt) => (
                    <option value={opt.value}>{opt.label}</option>
                  ))
                }
              </Show>
            </select>
          </Match>

          {/* String[] as Zed Tag / List Editor */}
          <Match when={props.field.type === "string[]"}>
            <div class="flex flex-col gap-2">
              <div class="flex flex-wrap items-center gap-1.5 min-h-[30px] p-1.5 bg-[var(--bg)] border border-[var(--border)] rounded-md focus-within:border-[var(--sidebar-active)] transition-colors">
                <For each={currentArray()}>
                  {(item, index) => (
                    <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--media-bg)] border border-[var(--border)] text-xs font-mono text-[var(--fg)] group/tag">
                      <span>{item}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(index())}
                        title="Remove"
                        class="text-[var(--sidebar-non-existant)] hover:text-red-400 transition-colors p-0.5"
                      >
                        <FiX class="w-3 h-3" />
                      </button>
                    </span>
                  )}
                </For>
                <div class="flex items-center gap-1 flex-1 min-w-[160px]">
                  <input
                    type="text"
                    disabled={props.isSaving}
                    placeholder={
                      currentArray().length === 0
                        ? props.field.placeholder || "Add item and press Enter..."
                        : "Add another..."
                    }
                    value={newTagInput()}
                    onInput={(e) => setNewTagInput(e.currentTarget.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddTag();
                      } else if (
                        e.key === "Backspace" &&
                        newTagInput() === "" &&
                        currentArray().length > 0
                      ) {
                        handleRemoveTag(currentArray().length - 1);
                      }
                    }}
                    class="bg-transparent border-none text-[var(--fg)] text-xs font-mono px-1 py-0.5 focus:outline-none w-full placeholder:text-[var(--sidebar-non-existant)]"
                  />
                  <Show when={newTagInput().trim().length > 0}>
                    <button
                      type="button"
                      onClick={handleAddTag}
                      class="text-xs px-1.5 py-0.5 rounded bg-[var(--sidebar-active)] text-white hover:opacity-90 flex items-center gap-0.5"
                    >
                      <FiPlus class="w-3 h-3" />
                    </button>
                  </Show>
                </div>
              </div>
            </div>
          </Match>

          {/* Number Input */}
          <Match when={props.field.type === "number"}>
            <input
              type="number"
              disabled={props.isSaving}
              placeholder={props.field.placeholder}
              value={displayVal() ?? ""}
              onInput={(e) => setLocalText(e.currentTarget.value)}
              onBlur={handleTextCommit}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleTextCommit();
                  e.currentTarget.blur();
                } else if (e.key === "Escape") {
                  setLocalText(null);
                  e.currentTarget.blur();
                }
              }}
              class="bg-[var(--bg)] border border-[var(--border)] text-[var(--fg)] rounded px-3 py-1.5 text-xs w-28 focus:outline-none focus:border-[var(--sidebar-active)] shadow-sm font-mono transition-colors hover:border-[var(--border-hover)] disabled:opacity-50"
            />
          </Match>

          {/* Standard Text Input (Large & Comfortable) */}
          <Match when={true}>
            <input
              type="text"
              disabled={props.isSaving}
              placeholder={props.field.placeholder}
              value={displayVal() ?? ""}
              onInput={(e) => setLocalText(e.currentTarget.value)}
              onBlur={handleTextCommit}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleTextCommit();
                  e.currentTarget.blur();
                } else if (e.key === "Escape") {
                  setLocalText(null);
                  e.currentTarget.blur();
                }
              }}
              class="bg-[var(--bg)] border border-[var(--border)] text-[var(--fg)] rounded px-3 py-1.5 text-xs w-80 max-w-full focus:outline-none focus:border-[var(--sidebar-active)] shadow-sm font-mono transition-colors hover:border-[var(--border-hover)] disabled:opacity-50"
            />
          </Match>
        </Switch>
      </div>
    </div>
  );
}
