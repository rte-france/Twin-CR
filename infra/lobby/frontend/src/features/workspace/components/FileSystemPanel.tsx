/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import {
  FiChevronRight,
  FiEdit2,
  FiFile,
  FiFilePlus,
  FiFileText,
  FiFolder,
  FiFolderPlus,
  FiHome,
  FiTrash2,
  FiUpload,
  FiUploadCloud,
} from "solid-icons/fi";
import {
  type Component,
  createEffect,
  createMemo,
  createSignal,
  For,
  Show,
} from "solid-js";
import { useNavigate, useParams } from "@solidjs/router";

import { isEditableFile } from "@/features/workspace/utils/constants";
import type { LobbyStore } from "@/features/workspace/hooks/store";
import type { FileNode } from "../types";

const FileSystemPanel: Component<{ store: LobbyStore }> = (props) => {
  const navigate = useNavigate();
  const params = useParams<{ projectId: string; fileId?: string }>();

  let fileInputRef: HTMLInputElement | undefined;
  let folderInputRef: HTMLInputElement | undefined;

  const [dragOverId, setDragOverId] = createSignal<string | null>(null);

  const breadcrumbPath = createMemo(() => {
    const path: FileNode[] = [];
    let current: FileNode | null = props.store.currentFolderId()
      ? (props.store.flatMap()[props.store.currentFolderId() as string] ?? null)
      : null;
    while (current) {
      path.unshift(current);
      current = current._parentId
        ? (props.store.flatMap()[current._parentId] ?? null)
        : null;
    }
    return path;
  });

  const currentNodes = createMemo(() => {
    const folderId = props.store.currentFolderId();
    const nodes = folderId
      ? props.store.flatMap()[folderId]?.children
      : props.store.fileSystem();
    if (!nodes) return [];
    return [...nodes].sort((a, b) => {
      if (a.is_directory && !b.is_directory) return -1;
      if (!a.is_directory && b.is_directory) return 1;
      return a.name.localeCompare(b.name);
    });
  });

  function checkedState(node: FileNode): {
    checked: boolean;
    indeterminate: boolean;
  } {
    if (node.is_directory) {
      const filesInfo = props.store.getAllFileNodes(node.id);
      if (filesInfo.length === 0)
        return { checked: false, indeterminate: false };
      const selectedCount = filesInfo.filter(
        (f) => props.store.selectedArtifacts()[f.file.id],
      ).length;
      return {
        checked: selectedCount === filesInfo.length,
        indeterminate: selectedCount > 0 && selectedCount < filesInfo.length,
      };
    }
    return {
      checked: !!props.store.selectedArtifacts()[node.id],
      indeterminate: false,
    };
  }

  function onDragStart(e: DragEvent, id: string) {
    e.dataTransfer?.setData("text/plain", id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
  }

  function onDragOver(e: DragEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();
    setDragOverId(id);
  }

  function onDragLeave(e: DragEvent) {
    e.stopPropagation();
    setDragOverId(null);
  }

  async function onDrop(e: DragEvent, targetFolderId: string | "root") {
    e.preventDefault();
    e.stopPropagation();
    setDragOverId(null);

    const draggedId = e.dataTransfer?.getData("text/plain");
    if (draggedId) {
      await props.store.moveItem(draggedId, targetFolderId);
    } else if (e.dataTransfer) {
      await props.store.handleExternalDrop(
        e.dataTransfer,
        targetFolderId === "root" ? null : targetFolderId,
      );
    }
  }

  function onFileInputChange(e: Event) {
    const target = e.currentTarget as HTMLInputElement;
    if (target.files) props.store.uploadFiles(target.files);
    target.value = "";
  }

  function onFolderInputChange(e: Event) {
    const target = e.currentTarget as HTMLInputElement;
    if (target.files) props.store.uploadFolderInput(target.files);
    target.value = "";
  }

  return (
    <div class="flex flex-col flex-1 min-h-0 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      <div class="flex flex-col gap-3 p-4 bg-gray-50 border-b border-gray-200">
        <div class="flex items-center gap-2 font-medium text-gray-700">
          <FiFolder class="text-blue-600 text-lg" />
          File System
        </div>
        <div class="flex gap-2 w-full">
          <button
            type="button"
            class="flex-1 flex justify-center items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700 transition-colors"
            title="New File"
            onClick={() => props.store.createNewFile()}
          >
            <FiFilePlus class="text-sm" />
          </button>
          <button
            type="button"
            class="flex-1 flex justify-center items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            title="New Folder"
            onClick={() => props.store.promptCreateFolder()}
          >
            <FiFolderPlus class="text-sm" />
          </button>
          <button
            type="button"
            class="flex-1 flex justify-center items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            title="Upload File(s)"
            onClick={() => fileInputRef?.click()}
          >
            <FiUpload class="text-sm" /> File
          </button>
          <button
            type="button"
            class="flex-1 flex justify-center items-center gap-1.5 px-2 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            title="Upload Folder"
            onClick={() => folderInputRef?.click()}
          >
            <FiUploadCloud class="text-sm" /> Folder
          </button>

          <input
            ref={fileInputRef}
            type="file"
            class="hidden"
            multiple
            onChange={onFileInputChange}
          />
          <input
            type="file"
            class="hidden"
            multiple
            ref={(el) => {
              folderInputRef = el;
              el.setAttribute("webkitdirectory", "");
              el.setAttribute("directory", "");
            }}
            onChange={onFolderInputChange}
          />
        </div>
      </div>

      <div
        class={`flex items-center gap-1 px-4 py-2 text-sm border-b border-gray-200 overflow-x-auto transition-colors ${
          dragOverId() === "root"
            ? "bg-blue-100 border-blue-300"
            : "bg-gray-50 text-gray-600"
        }`}
        onDragOver={(e) => onDragOver(e, "root")}
        onDragLeave={onDragLeave}
        onDrop={(e) => onDrop(e, "root")}
      >
        <FiHome class="text-gray-400 mr-1" />
        <button
          class="hover:text-blue-600 hover:underline transition-colors whitespace-nowrap"
          onClick={() => props.store.navigateTo(null)}
        >
          Root
        </button>
        <For each={breadcrumbPath()}>
          {(node) => (
            <>
              <FiChevronRight class="text-gray-400 text-xs mx-0.5 shrink-0" />
              <button
                type="button"
                class={`hover:text-blue-600 hover:underline transition-colors whitespace-nowrap px-1 rounded ${
                  dragOverId() === node.id ? "bg-blue-200 text-blue-800" : ""
                }`}
                onClick={() => props.store.navigateTo(node.id)}
                onDragOver={(e) => onDragOver(e, node.id)}
                onDragLeave={onDragLeave}
                onDrop={(e) => onDrop(e, node.id)}
              >
                {node.name}
              </button>
            </>
          )}
        </For>
      </div>

      <div
        class="flex-1 overflow-y-auto p-2"
        onDragOver={(e) => onDragOver(e, "root")}
        onDragLeave={onDragLeave}
        onDrop={(e) => onDrop(e, "root")}
      >
        <Show
          when={currentNodes().length > 0}
          fallback={
            <div class="flex items-center justify-center h-32 text-sm text-gray-400 italic">
              Empty folder
            </div>
          }
        >
          <For each={currentNodes()}>
            {(node) => {
              const isDir = node.is_directory;
              const isEditable = !isDir && isEditableFile(node.name);
              const isActive = () => props.store.selectedFileId() === node.id;
              const state = () => checkedState(node);

              return (
                <div
                  class={`group flex items-center gap-3 p-2 my-0.5 rounded-md cursor-pointer select-none border border-transparent transition-colors ${
                    isActive() ? "bg-blue-50" : ""
                  } ${
                    dragOverId() === node.id
                      ? "bg-blue-100 border-blue-400"
                      : "hover:bg-gray-100"
                  } ${!isDir && !isEditable ? "opacity-70" : ""}`}
                  draggable={true}
                  onDragStart={(e) => onDragStart(e, node.id)}
                  onClick={async () => {
                    if (!isDir) {
                      await props.store.selectFile(node.id);
                      // Met à jour l'URL instantanément avec l'UUID du fichier
                      navigate(`/workspace/${params.projectId}/${node.id}`);
                    }
                  }}
                  onDblClick={() => {
                    if (isDir) props.store.navigateTo(node.id);
                  }}
                  onDragOver={isDir ? (e) => onDragOver(e, node.id) : undefined}
                  onDragLeave={isDir ? onDragLeave : undefined}
                  onDrop={isDir ? (e) => onDrop(e, node.id) : undefined}
                  title={
                    isDir
                      ? "Double-click to open"
                      : isEditable
                        ? "Click to edit"
                        : "Binary file (read-only)"
                  }
                >
                  <input
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
                    checked={state().checked}
                    ref={(el) => {
                      createEffect(() => {
                        el.indeterminate = state().indeterminate;
                      });
                    }}
                    title="Select as injected artifact"
                    onClick={(e) => {
                      e.stopPropagation();
                      props.store.toggleArtifactSelection(
                        node.id,
                        node.name,
                        isDir,
                        (e.currentTarget as HTMLInputElement).checked,
                      );
                    }}
                  />

                  <div class="flex items-center justify-center w-5 h-5">
                    <Show when={isDir}>
                      <FiFolder class="text-blue-500 text-lg fill-blue-500/20" />
                    </Show>
                    <Show when={!isDir && isEditable}>
                      <FiFileText class="text-gray-500 text-lg" />
                    </Show>
                    <Show when={!isDir && !isEditable}>
                      <FiFile class="text-gray-400 text-lg" />
                    </Show>
                  </div>

                  <span
                    class={`flex-1 text-sm truncate ${isDir ? "font-medium text-gray-800" : "text-gray-600"}`}
                  >
                    {node.name}
                  </span>

                  <Show when={isActive()}>
                    <span class="px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-white bg-blue-500 rounded shadow-sm">
                      ACTIVE
                    </span>
                  </Show>

                  <div class="flex items-center opacity-0 group-hover:opacity-100 transition-opacity gap-1">
                    <button
                      type="button"
                      class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      title="Rename"
                      onClick={(e) => {
                        e.stopPropagation();
                        props.store.renameItem(node.id);
                      }}
                    >
                      <FiEdit2 class="text-sm" />
                    </button>
                    <button
                      type="button"
                      class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                      title="Delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        props.store.deleteItem(node.id);
                      }}
                    >
                      <FiTrash2 class="text-sm" />
                    </button>
                  </div>
                </div>
              );
            }}
          </For>
        </Show>
      </div>
    </div>
  );
};

export default FileSystemPanel;
