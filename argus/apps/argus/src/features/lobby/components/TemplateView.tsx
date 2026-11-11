/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, createSignal } from "solid-js";
import { FileTree } from "./FileTree";
import { TemplateDetailsView } from "./TemplateDetailsView";
import { NewTemplateModal } from "./NewTemplateModal";
import { Icon } from "@iconify-icon/solid";
import { setExpandedNodes, setTree, tree } from "../stores/FileTreeStore";
import { getFolderChildren } from "@/services/session-manager";
import { TreeNode } from "../types";
import { ErrorPanel, errorMessage } from "./ErrorPanel";

export function TemplateView() {
  const [selectedTemplateId, setSelectedTemplateId] = createSignal<number | null>(null);
  const [templateParentNodeId, setTemplateParentNodeId] = createSignal<number | null>(null);
  const [showNewTemplateModal, setShowNewTemplateModal] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);

  const refreshFolder = async (nodeId: number) => {
    let children;
    try {
      children = await getFolderChildren(nodeId);

      const parentChain = findParentChain(tree(), nodeId) ?? [];

      setExpandedNodes((current) => {
        const next = new Set(current);
        // unfold all parent folders
        parentChain.forEach((id) => next.add(id));
        // unfold the target folder too
        next.add(nodeId);
        return next;
      });
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
      return;
    }

    setTree((current) => {
      // Carry over what was already loaded under each child. A refresh replaces
      // one level; blanking the levels below it would leave those subtrees in
      // expandedNodes, so they would render open and empty.
      const loaded = new Map(
        (findNode(current, nodeId)?.children ?? []).map((c) => [c.id, c.children]),
      );

      return updateNodeChildren(
        current,
        nodeId,
        children.map((c) => ({
          ...c,
          children: loaded.get(c.id) ?? [],
        })),
      );
    });
  };

  function findNode(nodes: TreeNode[], nodeId: number): TreeNode | undefined {
    for (const node of nodes) {
      if (node.id === nodeId) {
        return node;
      }
      const found = node.children ? findNode(node.children, nodeId) : undefined;
      if (found) {
        return found;
      }
    }
    return undefined;
  }

  function updateNodeChildren(
    nodes: TreeNode[],
    nodeId: number,
    children: TreeNode[],
  ): TreeNode[] {
    return nodes.map((node) => {
      if (node.id === nodeId) {
        return {
          ...node,
          children,
        };
      }

      return {
        ...node,
        children: node.children
          ? updateNodeChildren(node.children, nodeId, children)
          : [],
      };
    });
  }

  function findParentChain(
    nodes: TreeNode[],
    targetId: number,
    parents: number[] = [],
  ): number[] | undefined {
    for (const node of nodes) {
      if (node.id === targetId) {
        return parents;
      }

      if (node.children) {
        const found = findParentChain(
          node.children,
          targetId,
          [...parents, node.id],
        );

        if (found) {
          return found;
        }
      }
    }
    return undefined;
  }

  return (
    <div class="w-full h-full min-h-0 flex bg-slate-100 text-slate-800">
      {/* SIDEBAR */}
      <div class="w-72 bg-white border-r border-slate-300 flex flex-col overflow-hidden">
        <div class="px-5 py-4 border-b border-slate-200">
          <h2 class="flex items-center text-xs font-mono font-bold uppercase tracking-[0.25em] text-slate-600">
            <Icon class="mr-2 text-cyan-600" icon="lucide:folder-open" />
            Templates
          </h2>
        </div>

        <div class="flex-1 overflow-auto p-4">
          <div class="text-xs space-y-2 text-slate-600 min-w-max">
            <FileTree
              onTemplateClick={(templateId, templateParentNodeId) => {
                setSelectedTemplateId(templateId);
                setTemplateParentNodeId(templateParentNodeId);
              }}
              refreshFolder={refreshFolder}
              onTemplateDeletion={() => {
                setSelectedTemplateId(null);
                setTemplateParentNodeId(null);
              }}
            />
          </div>
        </div>

        <ErrorPanel message={error()} class="mb-2" />

        <div class="p-4 border-t border-slate-200">
          <button
            class="w-full px-4 py-2 text-xs font-mono font-bold uppercase tracking-wider bg-slate-800 hover:bg-cyan-600 text-white transition-colors"
            onClick={() => setShowNewTemplateModal(true)}
          >
            <Icon class="mr-2" icon="lucide:file-plus-2" />
            Create Template
          </button>
        </div>
      </div>

      <Show when={selectedTemplateId() && templateParentNodeId()}>
        <TemplateDetailsView
          templateId={selectedTemplateId()!}
          templateParentNodeId={templateParentNodeId()!}
          refreshFolder={refreshFolder}
        />
      </Show>

      <Show when={showNewTemplateModal()}>
        <NewTemplateModal
          onClose={() => {
            setShowNewTemplateModal(false);
          }}
          refreshFolder={refreshFolder}
          parentNodeId={null}
        />
      </Show>
    </div>
  );
}
