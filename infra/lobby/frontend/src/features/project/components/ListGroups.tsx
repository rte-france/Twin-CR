/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { For, Show, createSignal } from "solid-js";
import type { Component } from "solid-js";
import {
  FiTrash2,
  FiPlus,
  FiChevronRight,
  FiChevronDown,
  FiSearch,
  FiUserPlus,
} from "solid-icons/fi";
import {
  AiOutlineFolder,
  AiTwotoneFolder,
  AiOutlineFolderOpen,
} from "solid-icons/ai";
import type { createProjectStore, Group } from "../hooks/store";

const GroupNode: Component<{
  group: Group;
  level: number;
  store: ReturnType<typeof createProjectStore>;
  searchQuery: string;
}> = (props) => {
  const children = () =>
    props.store.groups().filter((g) => g.parent_id === props.group.id);
  const hasChildren = () => children().length > 0;

  const isSelected = () => props.store.selectedGroupId() === props.group.id;

  const [isDragOver, setIsDragOver] = createSignal(false);
  let dragTimer: number | undefined;

  // --- LOGIQUE DE RECHERCHE DANS L'ARBRE ---
  // Vérifie si un enfant (ou petit-enfant) correspond à la recherche
  const isDescendantMatch = () => {
    if (!props.searchQuery) return false;
    const q = props.searchQuery.toLowerCase();
    const check = (id: string): boolean => {
      const kids = props.store.groups().filter((g) => g.parent_id === id);
      for (const k of kids) {
        if (k.name.toLowerCase().includes(q)) return true;
        if (check(k.id)) return true;
      }
      return false;
    };
    return check(props.group.id);
  };

  const isMatch = () =>
    props.group.name.toLowerCase().includes(props.searchQuery.toLowerCase());

  // Affiche le dossier s'il correspond OU s'il contient un enfant qui correspond
  const shouldShow = () =>
    !props.searchQuery || isMatch() || isDescendantMatch();

  // Ouvre automatiquement le dossier si on cherche dedans, sinon respecte l'état du store
  const isExpanded = () =>
    props.searchQuery && isDescendantMatch()
      ? true
      : props.store.expandedGroups().has(props.group.id);

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    clearTimeout(dragTimer);
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.stopPropagation();
    dragTimer = setTimeout(() => setIsDragOver(false), 50) as unknown as number;
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    clearTimeout(dragTimer);
    setIsDragOver(false);
    const projectId = e.dataTransfer?.getData("text/plain");
    if (projectId) {
      props.store.duplicateProject(projectId, props.group.id);
    }
  };

  const handleClick = (e: MouseEvent) => {
    e.stopPropagation();
    props.store.setSelectedGroupId(props.group.id);
  };

  const handleDoubleClick = (e: MouseEvent) => {
    e.stopPropagation();
    if (hasChildren()) {
      props.store.toggleGroupExpand(props.group.id);
    }
  };

  const handleShare = (e: Event) => {
    e.stopPropagation();
    const targetUserId = prompt(
      `Enter the User ID to share "${props.group.name}" with:`,
    );
    if (targetUserId) {
      const role =
        prompt(
          `Enter role (viewer, editor, admin) [default: viewer]:`,
          "viewer",
        ) || "viewer";
      props.store.shareGroup(props.group.id, targetUserId, role);
    }
  };

  const handleAddSubGroup = (e: Event) => {
    e.stopPropagation();
    const name = prompt(`New sub-folder inside "${props.group.name}":`);
    if (name) props.store.createGroup(name, props.group.id);
  };

  const handleDelete = (e: Event) => {
    e.stopPropagation();
    props.store.deleteGroup(props.group.id);
  };

  return (
    <Show when={shouldShow()}>
      <div>
        <div
          class="group flex items-center justify-between py-1.5 pr-2 rounded-md cursor-pointer transition-all border border-transparent"
          classList={{
            "bg-slate-100 border-slate-300 shadow-sm":
              isSelected() && !isDragOver(),
            "hover:bg-slate-50 hover:border-slate-200":
              !isSelected() && !isDragOver(),
            "bg-blue-100 border-blue-400 border-dashed": isDragOver(),
          }}
          style={{ "padding-left": `${props.level * 12 + 8}px` }}
          onClick={handleClick}
          onDblClick={handleDoubleClick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div class="flex items-center gap-1.5 truncate">
            <div
              class="p-1 -ml-1 rounded hover:bg-slate-200 text-slate-400 cursor-pointer flex items-center justify-center"
              onClick={(e) => {
                e.stopPropagation();
                if (hasChildren())
                  props.store.toggleGroupExpand(props.group.id);
              }}
            >
              <Show when={hasChildren()} fallback={<div class="w-4 h-4" />}>
                <Show
                  when={isExpanded()}
                  fallback={<FiChevronRight class="size-4" />}
                >
                  <FiChevronDown class="size-4" />
                </Show>
              </Show>
            </div>

            <Show
              when={isSelected() || isExpanded()}
              fallback={<AiOutlineFolder class="size-4 text-slate-400" />}
            >
              <div class="text-blue-500">
                <Show
                  when={isExpanded()}
                  fallback={<AiTwotoneFolder class="size-4 opacity-90" />}
                >
                  <AiOutlineFolderOpen class="size-4 opacity-90" />
                </Show>
              </div>
            </Show>
            <span class="font-medium text-sm truncate select-none">
              {props.group.name}
            </span>
          </div>

          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleShare}
              class="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-green-600 transition-colors"
              title="Share folder"
            >
              <FiUserPlus class="size-3.5" />
            </button>
            <button
              onClick={handleAddSubGroup}
              class="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-blue-600 transition-colors"
              title="Add sub-folder"
            >
              <FiPlus class="size-3.5" />
            </button>
            <button
              onClick={handleDelete}
              class="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-red-600 transition-colors"
              title="Delete group"
            >
              <FiTrash2 class="size-3.5" />
            </button>
          </div>
        </div>

        <Show when={isExpanded() && hasChildren()}>
          <div class="flex flex-col">
            <For each={children()}>
              {(child) => (
                <GroupNode
                  group={child}
                  level={props.level + 1}
                  store={props.store}
                  searchQuery={props.searchQuery}
                />
              )}
            </For>
          </div>
        </Show>
      </div>
    </Show>
  );
};

export const ListGroups: Component<{
  store: ReturnType<typeof createProjectStore>;
}> = (props) => {
  const [searchQuery, setSearchQuery] = createSignal("");

  const handleCreateRoot = () => {
    const name = prompt("Name of the new root folder:");
    if (name) props.store.createGroup(name, null);
  };


  const rootGroups = () => {
      const allGroups = props.store.groups() || [];
      const accessibleIds = new Set(allGroups.map((g) => g.id));
      return allGroups.filter((g) => !g.parent_id || !accessibleIds.has(g.parent_id));
    };

  return (
    <div class="flex flex-col h-full bg-white text-slate-800 font-sans border border-slate-200">
      {/* HEADER ALIGNÉ AVEC LISTPROJECTS (104px) */}
      <div class="p-4 space-y-4 border-b border-slate-200 bg-slate-50 h-26 shrink-0">
        <div class="flex items-center justify-between text-xs text-slate-500">
          <span class="font-medium uppercase tracking-wider text-slate-400">
            Folders
          </span>
        </div>

        {/* BARRE DE RECHERCHE ET BOUTON D'AJOUT */}
        <div class="flex w-full gap-2 items-center">
          <div class="relative flex-1">
            <FiSearch class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 size-4" />
            <input
              type="text"
              placeholder="Search folders..."
              class="w-full bg-white border border-slate-300 rounded-md pl-9 pr-3 py-1.5 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 placeholder:text-slate-400 transition-all shadow-sm"
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
              disabled={props.store.loading()}
            />
          </div>
          <button
            onClick={handleCreateRoot}
            disabled={props.store.loading()}
            class="px-2.5 py-1.5 rounded-md border border-slate-300 bg-white hover:bg-slate-100 text-slate-600 disabled:opacity-50 transition-colors flex items-center justify-center shadow-sm shrink-0"
            title="New Root Folder"
          >
            <FiPlus class="size-[18px]" />
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-2 space-y-0.5 custom-scrollbar bg-white">
        <Show
          when={!props.store.loading()}
          fallback={
            <div class="p-4 text-slate-400 text-center text-xs">Loading...</div>
          }
        >
          <For each={rootGroups()}>
            {(group) => (
              <GroupNode
                group={group}
                level={0}
                store={props.store}
                searchQuery={searchQuery()}
              />
            )}
          </For>
        </Show>
      </div>
    </div>
  );
};
