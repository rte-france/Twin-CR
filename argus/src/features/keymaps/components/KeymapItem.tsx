/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, Show, For } from "solid-js";
import { FiCheck, FiEdit2, FiX } from "solid-icons/fi";
import type { CommandDefinition } from "@/types/keymap.type";

interface KeymapItemProps {
  command: CommandDefinition;
  currentKey: string;
  isSaving: boolean;
  onUpdate: (newKey: string) => Promise<void>;
  getEventString: (e: KeyboardEvent) => string;
}

export function KeymapItem(props: KeymapItemProps) {
  const [isRecording, setIsRecording] = createSignal(false);
  const [livePreview, setLivePreview] = createSignal<string>("");
  const [success, setSuccess] = createSignal(false);

  const displayKeys = () => {
    if (props.currentKey) return [props.currentKey];
    return props.command.defaultKeys;
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (e.key === "Escape") {
      setIsRecording(false);
      setLivePreview("");
      return;
    }

    const keyStr = props.getEventString(e);
    if (!keyStr) return;

    // A key event is only a modifier if e.key is Control, Shift, Alt, Meta, etc.
    const isModifierKey = [
      "control",
      "shift",
      "alt",
      "meta",
      "os",
    ].includes(e.key.toLowerCase());

    setLivePreview(keyStr);

    // Only commit once a non-modifier key is pressed (e.g. mod+shift+t)
    if (!isModifierKey) {
      commitShortcut(keyStr);
    }
  };

  const commitShortcut = (shortcut: string) => {
    setIsRecording(false);
    setLivePreview("");
    props.onUpdate(shortcut).then(() => {
      setSuccess(true);
      setTimeout(() => setSuccess(false), 1500);
    });
  };

  const isCustomized = () => {
    if (!props.currentKey) return false;
    return !props.command.defaultKeys.includes(props.currentKey);
  };

  const formatKeyCombination = (combo: string): string[] => {
    return combo.split("+").map((k) => k.trim());
  };

  return (
    <div class="border-b border-(--divider) hover:bg-[var(--media-bg)]/30 transition-colors py-3 px-4 flex items-center justify-between gap-6 group">
      <div class="flex-1 min-w-0 flex flex-col gap-0.5">
        <div class="flex items-center gap-2">
          <span class="text-[13px] font-medium text-[var(--fg)] tracking-tight">
            {props.command.name}
          </span>
          <span class="text-[10px] font-mono text-[var(--sidebar-non-existant)] opacity-70">
            {props.command.id}
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
          <Show when={isCustomized()}>
            <span class="text-[9px] font-mono uppercase px-1 py-0.2 rounded bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active)] font-semibold">
              modified
            </span>
          </Show>
        </div>
      </div>

      <div class="shrink-0 flex items-center gap-2">
        <Show
          when={!isRecording()}
          fallback={
            <div
              tabIndex={0}
              onKeyDown={handleKeyDown}
              class="flex items-center gap-2 px-3 py-1 bg-[var(--bg)] border-2 border-[var(--sidebar-active)] rounded-md text-xs font-mono text-[var(--fg)] shadow-sm outline-none"
              ref={(el) => setTimeout(() => el?.focus(), 10)}
            >
              <Show
                when={livePreview().length > 0}
                fallback={
                  <span class="text-[var(--sidebar-active)] font-semibold animate-pulse">
                    Press combination (e.g. Ctrl+Shift+T, Esc to cancel)...
                  </span>
                }
              >
                <div class="flex items-center gap-1">
                  <For each={formatKeyCombination(livePreview())}>
                    {(key) => (
                      <kbd class="px-2 py-0.5 text-xs font-mono rounded bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active)] border border-[var(--sidebar-active)]">
                        {key}
                      </kbd>
                    )}
                  </For>
                </div>
              </Show>
              <button
                type="button"
                onClick={() => {
                  setIsRecording(false);
                  setLivePreview("");
                }}
                class="text-[var(--sidebar-non-existant)] hover:text-[var(--fg)] ml-1"
              >
                <FiX class="w-3.5 h-3.5" />
              </button>
            </div>
          }
        >
          <div class="flex items-center gap-2">
            <For each={displayKeys()}>
              {(combo) => (
                <div class="flex items-center gap-1">
                  <For each={combo.split(" ")}>
                    {(chord, chordIdx) => (
                      <>
                        <Show when={chordIdx() > 0}>
                          <span class="text-[10px] text-[var(--sidebar-non-existant)] font-mono">then</span>
                        </Show>
                        <For each={formatKeyCombination(chord)}>
                          {(key) => (
                            <kbd class="px-2 py-0.5 text-[11px] font-mono rounded bg-[var(--media-bg)] border border-[var(--border)] text-[var(--fg)] shadow-xs">
                              {key}
                            </kbd>
                          )}
                        </For>
                      </>
                    )}
                  </For>
                </div>
              )}
            </For>
          </div>

          <button
            type="button"
            title="Edit shortcut"
            onClick={() => {
              setLivePreview("");
              setIsRecording(true);
            }}
            class="opacity-0 group-hover:opacity-100 p-1.5 rounded text-[var(--sidebar-fg)] hover:text-[var(--fg)] hover:bg-[var(--media-bg)] transition-opacity"
          >
            <FiEdit2 class="w-3.5 h-3.5" />
          </button>
        </Show>
      </div>
    </div>
  );
}
