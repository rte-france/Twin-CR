/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { For, Show } from "solid-js";
import { TreeNode } from "../types";
import { Icon } from "@iconify-icon/solid";

type Props = {
  node: TreeNode;
  expandedNodes: Set<number>;
  onToggle: (node: TreeNode) => void;
  onContextMenu: (node: TreeNode, x: number, y: number) => void;
};

export function TreeNodeItem(props: Props) {
  const isFolder = () => props.node.type === "folder";

  const isOpen = () => props.expandedNodes.has(props.node.id);

  return (
    <div class="ml-2">
      <div
        class="flex items-center gap-2 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded"
        onClick={() => props.onToggle(props.node)}
        onContextMenu={(e) => {
          e.preventDefault();
          props.onContextMenu(props.node, e.clientX, e.clientY);
        }}
      >
        <span>{isFolder() ? (isOpen() ? <Icon class="mr-1" icon="lucide:folder-open" /> : <Icon class="mr-1" icon="lucide:folder" />) : <Icon class="mr-1" icon="lucide:file-text" />}</span>

        <span>{props.node.name}</span>
      </div>

      <Show when={isFolder() && isOpen()}>
        <div class="ml-4 border-l border-gray-200 pl-2">
          <For each={props.node.children ?? []}>
            {(child) => (
              <TreeNodeItem
                node={child}
                expandedNodes={props.expandedNodes}
                onToggle={props.onToggle}
                onContextMenu={props.onContextMenu}
              />
            )}
          </For>
        </div>
      </Show>
    </div>
  );
}
