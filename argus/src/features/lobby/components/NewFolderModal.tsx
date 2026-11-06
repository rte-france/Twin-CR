/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect } from "solid-js";
import { TreeNode } from "../types";
import { newFolder } from "@/services/session-manager/service";
import { ErrorPanel, errorMessage } from "./ErrorPanel";

type NewFolderModalProps = {
  onClose: () => void;
  parentNode: TreeNode;
  refreshFolder: (nodeId: number) => Promise<void>;
};

export function NewFolderModal(props: NewFolderModalProps) {
  const [newFolderName, setNewFolderName] = createSignal("");
  const [error, setError] = createSignal<string | null>(null);
  let inputRef: HTMLInputElement | undefined;

  createEffect(() => {
    queueMicrotask(() => {
      inputRef?.focus();
    });
  });

  const createFolderAction = async () => {
    if (!props.parentNode) {
      return;
    }

    try {
      await newFolder({
        name: newFolderName(),
        parent_id: props.parentNode.id,
      });
    } catch (err) {
      setError(errorMessage(err));
      return;
    }

    await props.refreshFolder(props.parentNode.id);
    setNewFolderName("");
    setError(null);
    props.onClose();
  }

  const cancelAction = () => {
    setNewFolderName("");
    setError(null);
    props.onClose();
  }

  return (
    <div class="fixed inset-0 bg-black/20 flex items-center justify-center z-50">
      <div class="bg-white shadow-lg p-4 w-80">
        <h3 class="text-sm font-semibold mb-3">New folder</h3>

        <input
          ref={inputRef}
          class="w-full border rounded px-2 py-1 mb-4"
          placeholder="Folder name"
          value={newFolderName()}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              createFolderAction();
            }
            if (e.key === "Escape") {
              cancelAction();
            }
          }}
          onInput={(e) => {
            setError(null);
            setNewFolderName(e.currentTarget.value);
          }}
        />

        <ErrorPanel message={error()} class="mb-3" />

        <div class="flex justify-end gap-2">
          <button
            class="bg-gray-200 px-3 py-1 text-xs enabled:hover:bg-gray-300 disabled:opacity-50"
            onClick={cancelAction}
          >
            Cancel
          </button>

          <button
            class="px-3 py-1 bg-slate-800 enabled:hover:bg-cyan-600 text-white font-mono text-xs font-bold uppercase tracking-wider transition-colors"
            onClick={createFolderAction}
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
}
