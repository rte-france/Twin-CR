/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createMemo, For, Show } from "solid-js";
import {
  FiSearch,
  FiX,
  FiCode,
  FiCommand,
  FiChevronRight,
  FiChevronDown,
  FiFolder,
  FiLayers,
  FiTag,
} from "solid-icons/fi";
import { useKeymapSettings } from "../hooks/useKeymapSettings";
import { KeymapItem } from "./KeymapItem";
import type { CommandDefinition } from "@/types/keymap.type";

interface KeymapTreeNode {
  id: string; // e.g. "application" or "application:panel"
  label: string; // e.g. "application" or "panel"
  fullPath: string[]; // ["application", "panel"]
  commands: CommandDefinition[]; // direct and descendant commands
  children: KeymapTreeNode[];
}

function buildTree(commands: readonly CommandDefinition[]): KeymapTreeNode[] {
  const rootMap = new Map<string, any>();

  for (const cmd of commands) {
    const parts = cmd.category ? cmd.category.split(":") : ["other"];
    let curr = rootMap;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!curr.has(part)) {
        curr.set(part, {
          label: part,
          partPath: parts.slice(0, i + 1),
          children: new Map(),
          commands: [],
        });
      }
      const nodeObj = curr.get(part);
      nodeObj.commands.push(cmd);
      curr = nodeObj.children;
    }
  }

  function convertMap(map: Map<string, any>): KeymapTreeNode[] {
    return Array.from(map.values()).map((val) => ({
      id: val.partPath.join(":"),
      label: val.label,
      fullPath: val.partPath,
      commands: val.commands,
      children: convertMap(val.children),
    }));
  }

  return convertMap(rootMap);
}

export function KeymapsSettings() {
  const {
    commands,
    config,
    savingId,
    error,
    updateBinding,
    getEventString,
  } = useKeymapSettings();

  const [activeNodeId, setActiveNodeId] = createSignal<string>("");
  const [collapsedNodes, setCollapsedNodes] = createSignal<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = createSignal("");
  const [viewJsonMode, setViewJsonMode] = createSignal(false);

  const fullTree = createMemo(() => buildTree(commands()));

  const toggleCollapse = (nodeId: string, e: MouseEvent) => {
    e.stopPropagation();
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const isCollapsed = (nodeId: string) => collapsedNodes().has(nodeId);

  // Filter commands by search query
  const matchingCommands = createMemo(() => {
    const q = searchQuery().trim().toLowerCase();
    const list = commands();
    if (!q) return list;

    return list.filter(
      (cmd) =>
        cmd.name.toLowerCase().includes(q) ||
        cmd.id.toLowerCase().includes(q) ||
        cmd.category.toLowerCase().includes(q) ||
        cmd.defaultKeys.some((k) => k.toLowerCase().includes(q)),
    );
  });

  // Displayed commands in main view based on selected tree node
  const displayedCommands = createMemo(() => {
    const q = searchQuery().trim().toLowerCase();
    const filtered = matchingCommands();

    const selectedId = activeNodeId();
    if (!selectedId && !q) {
      // Default to first node or all
      const tree = fullTree();
      if (tree.length > 0) {
        return tree[0].commands;
      }
      return filtered;
    }

    if (!selectedId) {
      return filtered;
    }

    return filtered.filter(
      (cmd) =>
        cmd.category === selectedId ||
        cmd.category.startsWith(selectedId + ":"),
    );
  });

  const currentNodeTitle = createMemo(() => {
    const id = activeNodeId();
    if (!id) {
      const tree = fullTree();
      return tree.length > 0 ? tree[0].label : "All Shortcuts";
    }
    return id
      .split(":")
      .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
      .join(" > ");
  });

  const treeJson = createMemo(() => {
    const root: Record<string, any> = {};
    const globalBindings = config()["Global"] || [];
    const bindingMap = new Map<string, string>();
    for (const b of globalBindings) {
      bindingMap.set(b.commandId, b.keyCombination);
    }

    for (const cmd of commands()) {
      const parts = cmd.id.split(":");
      let curr = root;
      for (let i = 0; i < parts.length - 1; i++) {
        const p = parts[i];
        if (!curr[p]) curr[p] = {};
        curr = curr[p];
      }
      const actionKey = parts[parts.length - 1];
      const activeKey = bindingMap.get(cmd.id) || cmd.defaultKeys[0] || "";
      curr[actionKey] = {
        description: cmd.name,
        keys: activeKey,
      };
    }
    return root;
  });

  const getCurrentKey = (commandId: string): string => {
    const globalBindings = config()["Global"] || [];
    const found = globalBindings.find((b) => b.commandId === commandId);
    return found?.keyCombination || "";
  };

  const handleUpdate = (commandId: string, newKey: string) => {
    return updateBinding("Global", commandId, newKey);
  };

  const renderTreeItem = (node: KeymapTreeNode, depth = 0) => {
    const isActive = () => {
      if (!activeNodeId() && depth === 0 && fullTree()[0]?.id === node.id) {
        return true;
      }
      return activeNodeId() === node.id;
    };
    const hasChildren = node.children.length > 0;

    return (
      <div class="flex flex-col">
        <button
          type="button"
          onClick={() => setActiveNodeId(node.id)}
          style={{ "padding-left": `${depth * 12 + 8}px` }}
          class={`w-full text-left py-1.5 pr-2 rounded text-xs transition-colors flex items-center justify-between group ${
            isActive() && !viewJsonMode()
              ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active)] font-medium"
              : "text-[var(--sidebar-fg)] hover:bg-[var(--media-bg)] hover:text-[var(--fg)]"
          }`}
        >
          <div class="flex items-center gap-1.5 truncate">
            <Show
              when={hasChildren}
              fallback={<span class="w-3.5 h-3.5 inline-block shrink-0" />}
            >
              <button
                type="button"
                onClick={(e) => toggleCollapse(node.id, e)}
                class="p-0.5 hover:text-[var(--fg)] rounded"
              >
                <Show
                  when={isCollapsed(node.id)}
                  fallback={<FiChevronDown class="w-3 h-3" />}
                >
                  <FiChevronRight class="w-3 h-3" />
                </Show>
              </button>
            </Show>
            <Show
              when={depth === 0}
              fallback={
                <Show
                  when={hasChildren}
                  fallback={<FiTag class="w-3.5 h-3.5 shrink-0 opacity-70 text-[var(--sidebar-fg)]" />}
                >
                  <FiLayers class="w-3.5 h-3.5 shrink-0 opacity-70 text-[var(--sidebar-fg)]" />
                </Show>
              }
            >
              <Show
                when={isCollapsed(node.id)}
                fallback={<FiFolder class="w-3.5 h-3.5 shrink-0 opacity-70 text-[var(--sidebar-active)]" />}
              >
                <FiFolder class="w-3.5 h-3.5 shrink-0 opacity-70" />
              </Show>
            </Show>
            <span class="truncate capitalize">{node.label}</span>
          </div>
          <span class="text-[10px] text-[var(--sidebar-non-existant)] font-mono shrink-0 ml-1">
            {node.commands.length}
          </span>
        </button>

        <Show when={hasChildren && !isCollapsed(node.id)}>
          <For each={node.children}>
            {(child) => renderTreeItem(child, depth + 1)}
          </For>
        </Show>
      </div>
    );
  };

  return (
    <div class="flex h-full w-full bg-[var(--bg)] text-[var(--fg)] font-sans antialiased select-none">
      <aside class="w-60 shrink-0 border-r border-[var(--border)] bg-[var(--sidebar-bg)] flex flex-col justify-between">
        <div class="flex flex-col flex-1 min-h-0">
          <div class="h-10 px-4 border-b border-[var(--border)] flex items-center justify-between text-[13px] font-semibold text-[var(--title-color)]">
            <div class="flex items-center gap-2">
              <FiCommand class="w-4 h-4 text-[var(--sidebar-active)]" />
              <span>Keyboard Shortcuts</span>
            </div>
            <button
              type="button"
              onClick={() => setViewJsonMode(!viewJsonMode())}
              title={viewJsonMode() ? "GUI Keymaps" : "JSON Preview"}
              class={`p-1 rounded text-xs transition-colors ${
                viewJsonMode()
                  ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active)]"
                  : "text-[var(--sidebar-fg)] hover:text-[var(--fg)] hover:bg-[var(--media-bg)]"
              }`}
            >
              <FiCode class="w-3.5 h-3.5" />
            </button>
          </div>

          <div class="p-2 border-b border-[var(--border)]">
            <div class="relative flex items-center">
              <FiSearch class="absolute left-2.5 w-3.5 h-3.5 text-[var(--sidebar-non-existant)] pointer-events-none" />
              <input
                type="text"
                placeholder="Search shortcuts..."
                value={searchQuery()}
                onInput={(e) => setSearchQuery(e.currentTarget.value)}
                class="w-full bg-[var(--bg)] border border-[var(--border)] text-[var(--fg)] text-xs rounded pl-8 pr-7 py-1.5 focus:outline-none focus:border-[var(--sidebar-active)] placeholder:text-[var(--sidebar-non-existant)]"
              />
              <Show when={searchQuery().length > 0}>
                <FiX
                  class="absolute right-2.5 w-3.5 h-3.5 cursor-pointer text-[var(--sidebar-non-existant)] hover:text-[var(--fg)] transition-colors"
                  onClick={() => setSearchQuery("")}
                />
              </Show>
            </div>
          </div>

          <nav class="flex-1 overflow-y-auto p-2 space-y-0.5">
            <For each={fullTree()}>
              {(rootNode) => renderTreeItem(rootNode, 0)}
            </For>
          </nav>
        </div>

        <div class="p-3 border-t border-[var(--border)] text-[11px] text-[var(--sidebar-non-existant)] flex items-center justify-between">
          <span>Config</span>
          <span class="font-mono text-[10px] text-[var(--success-color,#10b981)]">
            keymaps.json
          </span>
        </div>
      </aside>

      <main class="flex-1 flex flex-col min-w-0 bg-[var(--bg)] overflow-hidden">
        <Show when={error()}>
          <div class="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-xs text-red-400">
            {error()}
          </div>
        </Show>

        <Show
          when={!viewJsonMode()}
          fallback={
            <div class="flex-1 flex flex-col overflow-hidden">
              <div class="h-10 px-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--table-header-bg)] text-xs text-[var(--sidebar-fg)]">
                <span class="font-mono">keymaps.json (raw bindings)</span>
                <span class="text-[11px] text-[var(--sidebar-non-existant)]">
                  Live in-memory configuration
                </span>
              </div>
              <pre class="flex-1 p-4 font-mono text-xs overflow-auto text-[var(--fg)] bg-[var(--bg)] select-text">
                {JSON.stringify(treeJson(), null, 2)}
              </pre>
            </div>
          }
        >
          <Show
            when={displayedCommands().length > 0}
            fallback={
              <div class="p-8 text-center text-xs text-[var(--sidebar-non-existant)]">
                No matching shortcuts found.
              </div>
            }
          >
            <div class="flex-1 flex flex-col min-w-0 overflow-y-auto">
              <header class="py-2 px-4 h-10 border-b border-[var(--border)] bg-[var(--sidebar-bg)] shrink-0 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <h2 class="text-sm font-semibold text-[var(--title-color)]">
                    {currentNodeTitle()}
                  </h2>
                </div>
                <span class="text-xs text-[var(--sidebar-non-existant)] font-mono">
                  {displayedCommands().length} shortcut(s)
                </span>
              </header>

              <div class="divide-y divide-[var(--border)]">
                <For each={displayedCommands()}>
                  {(cmd) => (
                    <KeymapItem
                      command={cmd}
                      currentKey={getCurrentKey(cmd.id)}
                      isSaving={savingId() === cmd.id}
                      onUpdate={(newKey) => handleUpdate(cmd.id, newKey)}
                      getEventString={getEventString}
                    />
                  )}
                </For>
              </div>
            </div>
          </Show>
        </Show>
      </main>
    </div>
  );
}
