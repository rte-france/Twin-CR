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
  FiBox,
  FiTrash2,
  FiPlus,
  FiEdit2,
  FiExternalLink,
  FiChevronRight,
  FiSearch,
} from "solid-icons/fi";
import { AiTwotoneFolder, AiOutlineFolderOpen } from "solid-icons/ai";
import { A, useNavigate } from "@solidjs/router";
import type { createProjectStore, Group } from "../hooks/store";

// --- COMPOSANT : Sous-dossier (Affiché dans la colonne de gauche du split) ---
const SubFolderItem: Component<{
  folder: Group;
  store: ReturnType<typeof createProjectStore>;
}> = (props) => {
  const [isDragOver, setIsDragOver] = createSignal(false);
  let dragTimer: number | undefined;

  return (
    <div
      onClick={() => props.store.setSelectedGroupId(props.folder.id)}
      onDragOver={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
        clearTimeout(dragTimer);
        setIsDragOver(true);
      }}
      onDragLeave={(e) => {
        e.stopPropagation();
        dragTimer = setTimeout(
          () => setIsDragOver(false),
          50,
        ) as unknown as number;
      }}
      onDrop={(e) => {
        e.preventDefault();
        e.stopPropagation();
        clearTimeout(dragTimer);
        setIsDragOver(false);
        const projectId = e.dataTransfer?.getData("text/plain");
        if (projectId) props.store.duplicateProject(projectId, props.folder.id);
      }}
      class="group flex items-center justify-between p-2 rounded-md transition-all border cursor-pointer select-none mb-0.5"
      classList={{
        "border-transparent hover:bg-slate-200/50": !isDragOver(),
        "bg-blue-100 border-blue-400 border-dashed": isDragOver(),
      }}
    >
      <div class="flex items-center gap-2.5 truncate">
        <AiTwotoneFolder class="size-5 text-blue-400 shrink-0" />
        <span class="font-medium text-sm text-slate-700 truncate">
          {props.folder.name}
        </span>
      </div>
      <div class="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            props.store.deleteGroup(props.folder.id);
          }}
          class="p-1 hover:bg-white rounded text-slate-400 hover:text-red-600 transition-colors shadow-sm"
          title="Delete folder"
        >
          <FiTrash2 class="size-3.5" />
        </button>
      </div>
    </div>
  );
};

export const ListProjects: Component<{
  store: ReturnType<typeof createProjectStore>;
}> = (props) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = createSignal("");

  const handleCreateProject = () => {
    const groupId = props.store.selectedGroupId();
    if (!groupId) return;
    const name = prompt("Name of the new project:");
    if (name) {
      props.store.createProject(name, groupId);
    }
  };

  const handleUpdate = (project: {
    id: string;
    name: string;
    group_id: string;
  }) => {
    const newName = prompt("New name for project:", project.name);
    if (newName && newName !== project.name) {
      props.store.updateProject(project.id, newName, null);
    }
  };

  // --- NOUVEAU : Filtrage dynamique basé sur la recherche ---
  const currentFolders = () =>
    props.store
      .groups()
      .filter(
        (g) =>
          g.parent_id === props.store.selectedGroupId() &&
          g.name.toLowerCase().includes(searchQuery().toLowerCase()),
      );

  const currentProjects = () =>
    props.store
      .projects()
      .filter(
        (p) =>
          p.group_id === props.store.selectedGroupId() &&
          p.name.toLowerCase().includes(searchQuery().toLowerCase()),
      );

  // Génération du Fil d'Ariane
  const breadcrumbs = () => {
    const currentId = props.store.selectedGroupId();
    if (!currentId) return [];

    const groups = props.store.groups();
    const path = [];
    let curr = groups.find((g) => g.id === currentId);

    while (curr) {
      path.unshift(curr);
      curr = groups.find((g) => g.id === curr!.parent_id);
    }
    return path;
  };

  return (
    <div class="flex flex-col h-full bg-white text-slate-800 font-sans border border-slate-200">
      {/* HEADER AVEC BREADCRUMB */}
      <div class="p-4 space-y-4 border-b border-slate-200 bg-slate-50 h-26 shrink-0">
        <div class="flex items-center justify-between text-xs text-slate-500">
          <div class="flex items-center gap-1 overflow-hidden whitespace-nowrap">
            <span class="font-medium uppercase tracking-wider text-slate-400">
              Folders
            </span>
            <For each={breadcrumbs()}>
              {(crumb, index) => (
                <div class="flex items-center gap-1">
                  <FiChevronRight class="size-3.5 text-slate-300" />
                  <span
                    class="font-medium tracking-wider cursor-pointer hover:text-blue-600 transition-colors"
                    classList={{
                      "text-slate-600": index() === breadcrumbs().length - 1,
                      "text-slate-400": index() !== breadcrumbs().length - 1,
                    }}
                    onClick={() => props.store.setSelectedGroupId(crumb.id)}
                  >
                    {crumb.name}
                  </span>
                </div>
              )}
            </For>
          </div>
        </div>

        {/* --- NOUVEAU : BARRE DE RECHERCHE & BOUTON D'ACTION --- */}
        <Show when={props.store.selectedGroupId()}>
          <div class="flex w-full gap-3 items-center">
            <div class="relative flex-1">
              <FiSearch class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 size-4" />
              <input
                type="text"
                placeholder="Search projects or folders..."
                class="w-full bg-white border border-slate-300 rounded-md pl-9 pr-3 py-1.5 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 placeholder:text-slate-400 transition-all shadow-sm"
                value={searchQuery()}
                onInput={(e) => setSearchQuery(e.currentTarget.value)}
                disabled={props.store.loading()}
              />
            </div>
            <button
              onClick={handleCreateProject}
              disabled={props.store.loading()}
              class="px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 transition-colors flex items-center justify-center shadow-sm text-sm font-medium gap-1.5 shrink-0"
            >
              <FiPlus class="size-4" /> New Project
            </button>
          </div>
        </Show>
      </div>

      {/* ZONE PRINCIPALE - SPLIT VIEW */}
      <div class="flex-1 flex overflow-hidden bg-white">
        <Show
          when={!props.store.loading()}
          fallback={
            <div class="w-full text-slate-400 text-center text-xs mt-10">
              Loading...
            </div>
          }
        >
          {/* SI AUCUN DOSSIER N'EST SÉLECTIONNÉ */}
          <Show when={!props.store.selectedGroupId()}>
            <div class="w-full flex flex-col items-center justify-center text-slate-400 gap-2 opacity-60">
              <AiOutlineFolderOpen class="size-12 text-slate-300" />
              <p class="text-sm">
                Select a folder in the sidebar to view projects
              </p>
            </div>
          </Show>

          {/* CONTENU DU DOSSIER */}
          <Show when={props.store.selectedGroupId()}>
            {/* COLONNE GAUCHE (SOUS-DOSSIERS) */}
            <Show when={currentFolders().length > 0}>
              <div class="w-1/3 min-w-[200px] border-r border-slate-200 bg-slate-50/30 p-2 overflow-y-auto custom-scrollbar">
                <h3 class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 px-1">
                  Sub-Folders
                </h3>
                <For each={currentFolders()}>
                  {(folder) => (
                    <SubFolderItem folder={folder} store={props.store} />
                  )}
                </For>
              </div>
            </Show>

            {/* COLONNE DROITE (PROJETS) */}
            <div class="flex-1 p-2 overflow-y-auto custom-scrollbar">
              <Show
                when={currentProjects().length > 0}
                fallback={
                  <div class="text-sm text-slate-400 text-center py-10">
                    {searchQuery()
                      ? "No results found for your search."
                      : "No projects in this folder."}
                  </div>
                }
              >
                <h3 class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 px-1">
                  Projects
                </h3>
                <div class="flex flex-col gap-0.5">
                  <For each={currentProjects()}>
                    {(project) => (
                      <div
                        draggable="true"
                        onDragStart={(e) => {
                          e.dataTransfer?.setData("text/plain", project.id);
                          if (e.dataTransfer)
                            e.dataTransfer.effectAllowed = "copy";
                        }}
                        onDblClick={() => navigate(`/workspace/${project.id}`)}
                        class="group flex items-center justify-between p-2 rounded-md transition-all border border-transparent hover:bg-slate-50 hover:border-slate-200 cursor-pointer select-none"
                      >
                        <div class="flex items-center gap-3 truncate">
                          <FiBox class="size-5 text-slate-400 shrink-0" />
                          <span class="font-medium text-sm truncate">
                            {project.name}
                          </span>
                        </div>

                        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <A
                            href={`/workspace/${project.id}`}
                            class="px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded text-xs font-medium flex items-center gap-1 mr-2 transition-colors"
                          >
                            <FiExternalLink class="size-3" /> Edit
                          </A>
                          <button
                            class="p-1.5 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-700 transition-colors"
                            onClick={() => handleUpdate(project)}
                          >
                            <FiEdit2 class="size-4" />
                          </button>
                          <button
                            class="p-1.5 hover:bg-slate-200 rounded text-slate-400 hover:text-red-600 transition-colors"
                            onClick={() =>
                              props.store.deleteProject(project.id)
                            }
                          >
                            <FiTrash2 class="size-4" />
                          </button>
                        </div>
                      </div>
                    )}
                  </For>
                </div>
              </Show>
            </div>
          </Show>
        </Show>
      </div>
    </div>
  );
};
