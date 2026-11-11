/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount, onCleanup } from "solid-js";
import { TreeNode } from "../types";
import { deleteNode } from "@/services/session-manager/service";
import { ErrorPanel, errorMessage } from "./ErrorPanel";

type DeleteNodeModalProps = {
  onClose: () => void;
  folderNode: TreeNode;
  refreshFolder: (nodeId: number) => Promise<void>;
  onTemplateDeletion: () => void;
};

export function DeleteNodeModal(props: DeleteNodeModalProps) {
  const [error, setError] = createSignal<string | null>(null);

  onMount(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        deleteAction();
      }

      if (e.key === "Escape") {
        cancelAction();
      }
    };

    window.addEventListener("keydown", handler);
    onCleanup(() => window.removeEventListener("keydown", handler));
  });

  const deleteAction = async () => {
    let result;
    try {
      result = await deleteNode(props.folderNode.id);
    } catch (err) {
      setError(errorMessage(err));
      return;
    }

    if (result.parent_id != null) {
      await props.refreshFolder(result.parent_id);
    }
    props.onTemplateDeletion();
    props.onClose();
  }

  const cancelAction = () => {
    props.onClose();
  }

  return (
    <div class="fixed inset-0 bg-black/20 flex items-center justify-center z-50">
      <div class="bg-white shadow-lg p-4 w-80">
        <h3 class="text-sm font-semibold mb-3">
          Delete "{props.folderNode.name}" ?
        </h3>

        <ErrorPanel message={error()} class="mb-3" />

        <div class="flex justify-end gap-2">
          <button
            class="bg-gray-200 px-3 py-1 text-xs enabled:hover:bg-gray-300 disabled:opacity-50"
            onClick={cancelAction}
          >
            Cancel
          </button>

          <button
            class="px-3 py-1.5 text-xs font-medium border border-red-700 bg-red-700 text-white hover:bg-red-800 transition-colors flex items-center"
            onClick={deleteAction}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
