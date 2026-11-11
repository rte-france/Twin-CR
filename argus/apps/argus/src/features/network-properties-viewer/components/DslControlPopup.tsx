/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createMemo, For, Show, type Component, createEffect } from "solid-js";
import { Dialog } from "@kobalte/core/dialog";
import { FiX, FiCheck, FiPlus } from "solid-icons/fi";
import { DslCommand, sendDslCommand } from "./dslUtils";
import { CommandGroup, createInitialGroups, moveCommandsToExistingGroup, moveCommandsToNewGroup } from "./DslCommandGroup";

interface CommandResult {
  commandId: string;
  status: "idle" | "success" | "error";
  message?: string;
}

interface DslControlPopupProps {
  open: boolean;
  onClose: () => void;
  commands: DslCommand[];
  onSuccess: (successfulCommandIds: string[]) => void;
}

type ScheduleMode = "now" | "at" | "ramp";

interface GroupExecutionState {
  groupId: string;
  mode: ScheduleMode;
  atTime: string;
  rampStart: string;
  rampEnd: string;
}

function nowPlusSecs(s: number): string {
  return `now + ${s} seconds`;
}

export const DslControlPopup: Component<DslControlPopupProps> = (props) => {
  const [groups, setGroups] = createSignal<CommandGroup[]>(
    createInitialGroups(props.commands)
  );
  const [selected, setSelected] = createSignal<Set<string>>(new Set());
  const [lastSelected, setLastSelected] = createSignal<string | null>(null);
  const [results, setResults] = createSignal<Record<string, CommandResult>>(
    Object.fromEntries(props.commands.map((c) => [c.id, { commandId: c.id, status: "idle" }]))
  );
  const [editedText, setEditedText] = createSignal<Record<string, string>>({});
  const [execState, setExecState] = createSignal<Record<string, GroupExecutionState>>(
    Object.fromEntries(
      createInitialGroups(props.commands).map((g) => [
        g.id,
        { groupId: g.id, mode: "now" as ScheduleMode, atTime: nowPlusSecs(5), rampStart: nowPlusSecs(5), rampEnd: nowPlusSecs(10) },
      ])
    )
  );

  // Close when all actions are sent
  createEffect(() => {
    if (groups().length === 0) props.onClose();
  });

  const allCommandIds = createMemo(() =>
    groups().flatMap((g) => g.commands.map((c) => c.id))
  );

  // The text to display/send for a command: user edit takes priority over generated
  const getCommandText = (commandId: string, groupId: string): string => {
    const userEdit = editedText()[commandId];
    if (userEdit !== undefined) return userEdit;
    const group = groups().find((g) => g.id === groupId);
    const command = group?.commands.find((c) => c.id === commandId);
    if (!command) return "";
    const state = execState()[groupId];
    if (!state) return command.dslText;
    return buildDslText(command.dslText, state);
  };

  // Recompute edited text when exec state changes (mode/time inputs)
  // Only for commands that haven't been manually edited
  const buildDslText = (baseDslText: string, state: GroupExecutionState): string => {
    if (state.mode === "now") return baseDslText;
    if (state.mode === "at") return `at ${state.atTime}, ${baseDslText}`;
    if (state.mode === "ramp") return `at [${state.rampStart}, ${state.rampEnd}] with law "linear", ${baseDslText}`;
    return baseDslText;
  };

  const handleSelect = (commandId: string, e: MouseEvent) => {
    const ids = allCommandIds();
    setSelected((prev) => {
      const next = new Set(prev);
      if (e.shiftKey && lastSelected()) {
        const from = ids.indexOf(lastSelected()!);
        const to = ids.indexOf(commandId);
        const [start, end] = from < to ? [from, to] : [to, from];
        for (let i = start; i <= end; i++) next.add(ids[i]);
      } else if (e.ctrlKey || e.metaKey) {
        if (next.has(commandId)) next.delete(commandId); else next.add(commandId);
      } else {
        next.clear();
        next.add(commandId);
      }
      return next;
    });
    setLastSelected(commandId);
  };

  const ensureExecState = (groupId: string) => {
    if (!execState()[groupId]) {
      setExecState((prev) => ({
        ...prev,
        [groupId]: { groupId, mode: "now", atTime: nowPlusSecs(5), rampStart: nowPlusSecs(5), rampEnd: nowPlusSecs(10) },
      }));
    }
  };

  const handleMoveToNewGroup = () => {
    const sel = selected();
    if (sel.size === 0) return;
    const newGroups = moveCommandsToNewGroup(groups(), sel);
    setGroups(newGroups);
    const newGroup = newGroups[newGroups.length - 1];
    ensureExecState(newGroup.id);
    // Clear user edits for moved commands so they get rebuilt with new group's exec state
    setEditedText((prev) => {
      const next = { ...prev };
      sel.forEach((id) => delete next[id]);
      return next;
    });
    setSelected(new Set<string>());
  };

  const handleMoveToExistingGroup = (targetGroupId: string) => {
    const sel = selected();
    if (sel.size === 0) return;
    setGroups(moveCommandsToExistingGroup(groups(), sel, targetGroupId));
    // Clear user edits for moved commands so they get rebuilt with target group's exec state
    setEditedText((prev) => {
      const next = { ...prev };
      sel.forEach((id) => delete next[id]);
      return next;
    });
    setSelected(new Set<string>());
  };

  const updateGroupExecState = (groupId: string, patch: Partial<GroupExecutionState>) => {
    setExecState((prev) => ({ ...prev, [groupId]: { ...prev[groupId], ...patch } }));
    // Clear user edits for commands in this group so they pick up the new timing
    const group = groups().find((g) => g.id === groupId);
    if (group) {
      setEditedText((prev) => {
        const next = { ...prev };
        group.commands.forEach((c) => delete next[c.id]);
        return next;
      });
    }
  };

  const sendGroupCommands = async (groupId: string) => {
    const group = groups().find((g) => g.id === groupId);
    if (!group) return;

    // Capture all commands and their texts before any mutations
    const commandsToSend = group.commands.map((command) => ({
      command,
      dslText: getCommandText(command.id, groupId),
    }));

    const successIds: string[] = [];

    for (const { command, dslText } of commandsToSend) {
      try {
        await sendDslCommand(dslText);
        setResults((prev) => ({ ...prev, [command.id]: { commandId: command.id, status: "success" } }));
        successIds.push(command.id);
        setGroups((prev) => prev
          .map((g) => g.id === groupId
            ? { ...g, commands: g.commands.filter((c) => c.id !== command.id) }
            : g
          )
          .filter((g) => g.commands.length > 0)
        );
      } catch (e) {
        setResults((prev) => ({ ...prev, [command.id]: { commandId: command.id, status: "error", message: String(e) } }));
      }
    }

    props.onSuccess(successIds);
  };

  return (
    <Dialog open={props.open} onOpenChange={(o) => { if (!o) props.onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]" />
        <div class="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
          <Dialog.Content class="pointer-events-auto w-full max-w-2xl max-h-[80vh] flex flex-col rounded-lg bg-[var(--popover-bg)] p-6 text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)] outline-none">
            <div class="flex items-center justify-between mb-4 shrink-0">
              <Dialog.Title class="text-lg font-medium text-[var(--title-color)]">DSL Commands</Dialog.Title>
              <div class="flex items-center gap-2">
                <Show when={selected().size > 0}>
                  <div class="flex items-center gap-1">
                    <button
                      onClick={handleMoveToNewGroup}
                      class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded border border-[var(--border)] hover:bg-[var(--theme-hover)] transition-colors"
                    >
                      <FiPlus class="size-3" />
                      New group
                    </button>
                    <Show when={groups().length > 1}>
                      <select
                        class="text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded px-2 py-1.5 text-[var(--code-text)] focus:outline-none focus:border-[var(--links)]"
                        onChange={(e) => {
                          if (e.currentTarget.value) {
                            handleMoveToExistingGroup(e.currentTarget.value);
                            e.currentTarget.value = "";
                          }
                        }}
                      >
                        <option value="">Move to group…</option>
                        <For each={groups().filter((g) => !g.commands.every((c) => selected().has(c.id)))}>
                          {(g) => <option value={g.id}>{g.name}</option>}
                        </For>
                      </select>
                    </Show>
                  </div>
                </Show>
                <Dialog.CloseButton class="text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors rounded p-1 hover:bg-[var(--theme-hover)]">
                  <FiX class="size-4" />
                </Dialog.CloseButton>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto custom-scrollbar space-y-4">
              <For each={groups()}>
                {(group) => {
                  const state = () => execState()[group.id];
                  return (
                    <div class="rounded border border-[var(--border)]">
                      <div class="flex items-center justify-between px-3 py-2 border-b border-[var(--border)] bg-[var(--table-header-bg)]">
                        <span class="text-xs font-semibold text-[var(--fg)]">{group.name}</span>
                        <div class="flex items-center gap-2">
                          <select
                            value={state()?.mode ?? "now"}
                            onChange={(e) => updateGroupExecState(group.id, { mode: e.currentTarget.value as ScheduleMode })}
                            class="text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded px-2 py-1 text-[var(--code-text)] focus:outline-none focus:border-[var(--links)]"
                          >
                            <option value="now">Execute now</option>
                            <option value="at">Schedule for</option>
                            <option value="ramp">Ramp</option>
                          </select>
                          <Show when={state()?.mode === "at"}>
                            <input
                              type="text"
                              value={state()?.atTime}
                              onInput={(e) => updateGroupExecState(group.id, { atTime: e.currentTarget.value })}
                              class="text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded px-2 py-1 w-36 text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] font-mono"
                            />
                          </Show>
                          <Show when={state()?.mode === "ramp"}>
                            <input
                              type="text"
                              value={state()?.rampStart}
                              onInput={(e) => updateGroupExecState(group.id, { rampStart: e.currentTarget.value })}
                              class="text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded px-2 py-1 w-36 text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] font-mono"
                            />
                            <span class="text-xs opacity-40">→</span>
                            <input
                              type="text"
                              value={state()?.rampEnd}
                              onInput={(e) => updateGroupExecState(group.id, { rampEnd: e.currentTarget.value })}
                              class="text-xs bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded px-2 py-1 w-36 text-[var(--code-text)] focus:outline-none focus:border-[var(--links)] font-mono"
                            />
                          </Show>
                          <button
                            onClick={() => sendGroupCommands(group.id)}
                            class="px-3 py-1 text-xs rounded bg-[var(--links)] text-white hover:opacity-90 transition-all"
                          >
                            Send
                          </button>
                        </div>
                      </div>

                      <div class="divide-y divide-[var(--border)]">
                        <For each={group.commands}>
                          {(command) => {
                            const result = () => results()[command.id];
                            const isSelected = () => selected().has(command.id);
                            return (
                              <div
                                class={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors select-none ${
                                  isSelected() ? "bg-[var(--links)] bg-opacity-10" : "hover:bg-[var(--theme-hover)]"
                                }`}
                                onClick={(e) => handleSelect(command.id, e)}
                              >
                                <div class="w-3 shrink-0">
                                  <Show when={result()?.status === "success"}>
                                    <FiCheck class="size-3 text-[var(--success-color)]" />
                                  </Show>
                                  <Show when={result()?.status === "error"}>
                                    <span class="text-[var(--warning-icon)] text-xs" title={result()?.message}>✕</span>
                                  </Show>
                                </div>
                                <input
                                  type="text"
                                  value={getCommandText(command.id, group.id)}
                                  onInput={(e) => {
                                    setEditedText((prev) => ({ ...prev, [command.id]: e.currentTarget.value }));
                                  }}
                                  onClick={(e) => e.stopPropagation()}
                                  class="flex-1 text-xs font-mono bg-transparent border-none outline-none text-[var(--code-text)] focus:bg-[var(--pre-bg)] focus:px-1 rounded transition-all"
                                />
                              </div>
                            );
                          }}
                        </For>
                      </div>
                    </div>
                  );
                }}
              </For>
            </div>

            <div class="flex justify-end mt-4 shrink-0">
              <button onClick={props.onClose} class="px-4 py-2 text-sm font-medium rounded-md border border-[var(--border)] bg-[var(--search-btn-bg)] hover:bg-[var(--theme-hover)] transition-colors">
                Close
              </button>
            </div>
          </Dialog.Content>
        </div>
      </Dialog.Portal>
    </Dialog>
  );
};
