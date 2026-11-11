/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { For, createSignal, Show, onMount, onCleanup } from "solid-js";
import { TreeNodeItem } from "./TreeNodeItem";
import { TreeNode } from "../types";
import { NewFolderModal } from "@/features/lobby/components/NewFolderModal";
import { NewTemplateModal } from "./NewTemplateModal";
import { DeleteNodeModal } from "./DeleteNodeModal";
import { getTree } from "@/services/session-manager";
import { ErrorPanel, errorMessage } from "./ErrorPanel";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { Icon } from "@iconify-icon/solid";
import {
  expandedNodes,
  setExpandedNodes,
  setTree,
  tree,
} from "../stores/FileTreeStore";

export function FileTree(props: {
  onTemplateClick: (templateId: number, templateParentNodeId: number) => void;
  refreshFolder: (nodeId: number) => Promise<void>;
  onTemplateDeletion: () => void;
}) {
  const ROOT_FOLDER_ID = 0; // value hard coded in session manager
  const USERS_FOLDER_ID = 1; // value hard coded in session manager
  const [contextMenu, setContextMenu] = createSignal<{node: TreeNode; x: number; y: number;} | null>(null);
  const [showNewFolderModal, setShowNewFolderModal] = createSignal(false);
  const [showDeleteNodeModal, setShowDeleteNodeModal] = createSignal(false);
  const [showNewTemplateModal, setShowNewTemplateModal] = createSignal(false);
  const [selectedNode, setSelectedNode] = createSignal<TreeNode | null>(null);
  const [error, setError] = createSignal<string | null>(null);
  const auth = useAuth();

  onMount(async () => {
    // load the whole tree
    try {
      const roots = await getTree(ROOT_FOLDER_ID);
      setTree(roots);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
      return;
    }

    // handler to remove contextmenu on key "Escape" pressed
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setContextMenu(null);
      }
    };
    window.addEventListener("keydown", handler);
    onCleanup(() => window.removeEventListener("keydown", handler));
  });

  const toggleNode = async (node: TreeNode) => {
    if (node.type == "template") {
      props.onTemplateClick(node.template_id, node.parent_id);
    } else {
      const expanded = expandedNodes();

      if (!expanded.has(node.id)) {
        await props.refreshFolder(node.id);

        setExpandedNodes((current) => {
          const next = new Set(current);
          next.add(node.id);
          return next;
        });
      } else {
        setExpandedNodes((current) => {
          const next = new Set(current);
          next.delete(node.id);
          return next;
        });
      }
    }
  };

  return (
    <div class="text-sm" onClick={() => setContextMenu(null)}>
      <ErrorPanel message={error()} class="mb-2" />
      <Show when={contextMenu()}>
        {(menu) => (
          <div
            class="fixed bg-white border shadow-lg z-50"
            style={{
              left: `${menu().x}px`,
              top: `${menu().y}px`,
            }}
          >
            <Show when={menu().node.type == "folder"}>
              <button
                class="block w-full text-left px-1 py-0.5 hover:bg-gray-100"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedNode(menu().node);
                  setShowNewFolderModal(true);
                  setContextMenu(null);
                }}
              >
                <Icon class="mr-1" icon="lucide:folder-plus" />
                New folder
              </button>
            </Show>
            <Show when={ menu().node.parent_id !== ROOT_FOLDER_ID && menu().node.parent_id !== USERS_FOLDER_ID }>
              <button
                class="block w-full text-left px-1 py-0.5 hover:bg-gray-100"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedNode(menu().node);
                  setShowDeleteNodeModal(true);
                  setContextMenu(null);
                }}
              >
                <Icon class="mr-1" icon="lucide:trash" />
                Delete element
              </button>
            </Show>
            <Show when={ menu().node.type == "folder"}>
              <button
                class="block w-full text-left px-1 py-0.5 hover:bg-gray-100"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedNode(menu().node);
                  setShowNewTemplateModal(true);
                  setContextMenu(null);
                }}
              >
                <Icon class="mr-1" icon="lucide:file-text" />
                New template
              </button>
            </Show>
          </div>
        )}
      </Show>
      <Show when={showNewFolderModal() && selectedNode()}>
        {(node) => (
          <NewFolderModal
            onClose={() => {
              setShowNewFolderModal(false);
              setContextMenu(null);
            }}
            parentNode={node()}
            refreshFolder={props.refreshFolder}
          />
        )}
      </Show>
      <Show when={showDeleteNodeModal() && selectedNode()}>
        {(node) => (
          <DeleteNodeModal
            onClose={() => {
              setShowDeleteNodeModal(false);
              setContextMenu(null);
            }}
            folderNode={node()}
            refreshFolder={props.refreshFolder}
            onTemplateDeletion={props.onTemplateDeletion}
          />
        )}
      </Show>
      <Show when={showNewTemplateModal() && selectedNode()}>
        {(node) => (
          <NewTemplateModal
            onClose={() => {
              setShowNewTemplateModal(false);
              setContextMenu(null);
            }}
            parentNodeId={node().id}
            refreshFolder={props.refreshFolder}
          />
        )}
      </Show>

      {/* TREE */}
      <Show when={tree()}>
        <For each={tree()}>
          {(node) => (
            <TreeNodeItem
              node={node}
              expandedNodes={expandedNodes()}
              onToggle={toggleNode}
              onContextMenu={(node, x, y) => {
                if (node.owner == auth.username()) {
                  setContextMenu({
                    node,
                    x,
                    y,
                  });
                }
              }}
            />
          )}
        </For>
      </Show>
    </div>
  );
}
