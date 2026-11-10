/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { FiChevronRight, FiFileText, FiFolder, FiPlay } from "solid-icons/fi";
import { type Component, Show, For } from "solid-js";
import type { LobbyStore } from "@/features/workspace/hooks/store";

const Header: Component<{ store: LobbyStore; projectName?: string }> = (
  props,
) => {
  const hasFile = () =>
    !!(props.store.selectedFileId() && props.store.selectedFileName());

  // Génération du breadcrumb du dossier courant pour le Header
  const breadcrumbPath = () => {
    const path: Array<{ id: string; name: string }> = [];
    let currentId = props.store.currentFolderId();
    const flatMap = props.store.flatMap();

    while (currentId && flatMap[currentId]) {
      const node = flatMap[currentId];
      path.unshift({ id: node.id, name: node.name });
      currentId = node._parentId ?? null;
    }
    return path;
  };

  return (
    <header class="col-span-3 row-start-1 flex items-center justify-between px-5 bg-white border-b border-gray-200 shadow-sm z-10">
      {/* Section Gauche : Projet + Fil d'Ariane + Fichier actif */}
      <div class="flex items-center gap-3 text-xs truncate">
        {/* Nom du projet */}
        <div class="flex items-center gap-1.5 font-semibold text-gray-800 bg-gray-100 px-2.5 py-1 rounded-md shrink-0">
          <FiFolder class="text-blue-600 text-sm" />
          <span>{props.projectName ?? "Projet"}</span>
        </div>

        <span class="text-gray-300">/</span>

        {/* Fil d'Ariane des dossiers */}
        <div class="flex items-center gap-1 text-gray-500 overflow-x-auto">
          <span
            class="hover:text-gray-800 cursor-pointer"
            onClick={() => props.store.navigateTo(null)}
          >
            root
          </span>
          <For each={breadcrumbPath()}>
            {(folder) => (
              <>
                <FiChevronRight class="text-gray-400 text-xs shrink-0" />
                <span
                  class="hover:text-gray-800 cursor-pointer truncate max-w-[100px]"
                  onClick={() => props.store.navigateTo(folder.id)}
                >
                  {folder.name}
                </span>
              </>
            )}
          </For>
        </div>

        <span class="text-gray-300">/</span>

        {/* Fichier en cours d'édition */}
        <div class="flex items-center gap-1.5 truncate">
          <FiFileText
            class={`text-base shrink-0 ${hasFile() ? "text-gray-500" : "text-red-500"}`}
          />
          <span class="font-mono font-semibold text-gray-900 truncate max-w-[200px]">
            <Show
              when={hasFile()}
              fallback={
                <span class="text-red-500 font-medium italic">
                  No file selected
                </span>
              }
            >
              {props.store.selectedFileName()}
            </Show>
          </span>
        </div>
      </div>

      {/* Bouton d'action */}
      <button
        type="button"
        class="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white transition-colors bg-blue-600 rounded hover:bg-blue-700 shrink-0"
        onClick={() => props.store.launchNomadJob()}
      >
        <FiPlay class="text-sm" />
        Prepare Session
      </button>
    </header>
  );
};

export default Header;
