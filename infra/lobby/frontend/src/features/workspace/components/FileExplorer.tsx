/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { createResource, createSignal, For, Show } from "solid-js";
import { Effect, Context } from "effect";
import { LobbyService } from "@/features/workspace/services/lobby";
import type { FileNode } from "@/features/workspace/services/lobby";
import { getSystemRuntime } from "@/utils/getSystemRuntime";

const runLobby = <A, E>(f: (svc: Context.Tag.Service<typeof LobbyService>) => Effect.Effect<A, E>) =>
  getSystemRuntime().runPromise(LobbyService.pipe(Effect.andThen(f)));

function TreeNode(props: { node: FileNode; onSelectFolder: (id: string) => void; selectedFolderId: string | null }) {
  const [expanded, setExpanded] = createSignal(true);
  
  return (
    <div class="ml-4">
      <div 
        class={`flex items-center gap-2 py-1 px-2 hover:bg-gray-100 rounded cursor-pointer ${
          props.selectedFolderId === props.node.id ? "bg-gray-200" : ""
        }`}
        onClick={() => {
          if (props.node.is_directory) {
            props.onSelectFolder(props.node.id);
            setExpanded(!expanded());
          }
        }}
      >
        <span class="text-gray-500 w-4 text-center">
          {props.node.is_directory ? (expanded() ? "📂" : "📁") : "📄"}
        </span>
        <span class="text-sm select-none">{props.node.name}</span>
      </div>
      
      <Show when={props.node.is_directory && expanded() && props.node.children}>
        <For each={props.node.children}>
          {(child) => (
            <TreeNode
              node={child}
              onSelectFolder={props.onSelectFolder}
              selectedFolderId={props.selectedFolderId}
            />
          )}
        </For>
      </Show>
    </div>
  );
}

export function FileExplorer(props: { projectId: string | null }) {
  const [files, { refetch }] = createResource(
    () => props.projectId,
    (pid) => runLobby((svc) => svc.fetchFileSystem(pid))
  );

  const [selectedFolderId, setSelectedFolderId] = createSignal<string | null>(null);
  let fileInputRef!: HTMLInputElement;

  const handleCreateDirectory = async () => {
    if (!props.projectId) return;
    const name = prompt("Directory name:");
    if (!name) return;
    await runLobby((svc) => svc.createDirectory(props.projectId!, name, selectedFolderId()));
    refetch();
  };

  const handleFileUpload = async (e: Event) => {
    if (!props.projectId) return;
    const input = e.target as HTMLInputElement;
    if (!input.files?.length) return;
    
    for (const file of input.files) {
      await runLobby((svc) => svc.uploadFile(props.projectId!, file, file.name, selectedFolderId()));
    }
    input.value = "";
    refetch();
  };

  return (
    <div class="w-80 bg-white border-r border-gray-200 p-4 h-full flex flex-col gap-4 overflow-y-auto">
      <h2 class="text-lg font-semibold">File Explorer</h2>

      <Show when={props.projectId} fallback={<div class="text-sm text-gray-500">Select a project first.</div>}>
        <div class="flex gap-2">
          <button
            onClick={handleCreateDirectory}
            class="bg-blue-600 text-white px-3 py-1 rounded text-xs font-medium hover:bg-blue-700 w-full"
          >
            New Folder
          </button>
          <button
            onClick={() => fileInputRef.click()}
            class="bg-blue-600 text-white px-3 py-1 rounded text-xs font-medium hover:bg-blue-700 w-full"
          >
            Upload File
          </button>
          <input
            type="file"
            ref={fileInputRef}
            class="hidden"
            multiple
            onChange={handleFileUpload}
          />
        </div>

        <div class="flex items-center gap-2 mt-2">
          <button
            onClick={() => setSelectedFolderId(null)}
            class={`text-xs px-2 py-1 rounded border hover:bg-gray-100 ${
              selectedFolderId() === null ? "bg-gray-200" : ""
            }`}
          >
            Root
          </button>
          <span class="text-xs text-gray-500">
            {selectedFolderId() ? `Target ID: ${selectedFolderId()?.slice(0,6)}...` : "Target: Root"}
          </span>
        </div>

        <Show when={!files.loading} fallback={<div class="text-sm text-gray-500 mt-4">Loading files...</div>}>
          <div class="mt-4 -ml-4">
            <For each={files()}>
              {(node) => (
                <TreeNode
                  node={node}
                  onSelectFolder={setSelectedFolderId}
                  selectedFolderId={selectedFolderId()}
                />
              )}
            </For>
            <Show when={files()?.length === 0}>
              <div class="text-sm text-gray-400 italic pl-4">No files found.</div>
            </Show>
          </div>
        </Show>
      </Show>
    </div>
  );
}
