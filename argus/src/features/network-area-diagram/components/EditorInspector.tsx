/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, Show, createMemo } from "solid-js";
import { useEditorContext } from "../hooks/useEditorContext";
import { useNadContext } from "../hooks/useNadContext";

export const EditorInspector: Component = () => {
  const { editorState, selectNode, moveNode, commitMove } = useEditorContext();
  const nadCtx = useNadContext();

  const selectedNode = createMemo(() => {
    const id = editorState.selectedNodeId;
    if (!id) return null;
    return (
      nadCtx.nadData()?.metadata?.nodes?.find((n) => n.svgId === id) ?? null
    );
  });

  const currentPos = createMemo(() => {
    const id = editorState.selectedNodeId;
    if (!id) return null;
    const override = editorState.nodePositions[id];
    if (override) return override;
    const node = selectedNode();
    return node ? { x: node.x, y: node.y } : null;
  });

  const handleXChange = (val: string) => {
    const id = editorState.selectedNodeId;
    if (!id) return;
    const x = parseFloat(val);
    if (isNaN(x)) return;
    const prev = currentPos();
    if (!prev) return;
    moveNode(id, x, prev.y);
    commitMove(id, prev.x, prev.y);
  };

  const handleYChange = (val: string) => {
    const id = editorState.selectedNodeId;
    if (!id) return;
    const y = parseFloat(val);
    if (isNaN(y)) return;
    const prev = currentPos();
    if (!prev) return;
    moveNode(id, prev.x, y);
    commitMove(id, prev.x, prev.y);
  };

  return (
    <div class="editor-inspector w-56 shrink-0 bg-[var(--editor-panel-bg)] border-l border-[var(--editor-border)] flex flex-col overflow-hidden">
      {/* Header */}
      <div class="px-3 py-2 border-b border-[var(--editor-border)] flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-widest font-bold text-[var(--editor-text-muted)] font-mono">
          Propriétés
        </span>
        <Show when={editorState.selectedNodeId}>
          <button
            onClick={() => selectNode(null)}
            class="text-[var(--editor-text-muted)] hover:text-[var(--editor-text)] text-xs transition-colors"
          >
            ✕
          </button>
        </Show>
      </div>

      <div class="flex-1 overflow-y-auto">
        <Show
          when={selectedNode()}
          fallback={
            <div class="flex flex-col items-center justify-center h-32 text-center px-4">
              <div class="text-2xl mb-2 opacity-30">◈</div>
              <p class="text-[10px] text-[var(--editor-text-muted)] font-mono uppercase tracking-wider">
                Aucun node sélectionné
              </p>
              <p class="text-[9px] text-[var(--editor-text-muted)] font-mono mt-1 opacity-60">
                Clic droit ou S+clic
              </p>
            </div>
          }
        >
          {(node) => (
            <div class="flex flex-col gap-0 py-1">
              {/* Node identity section */}
              <InspectorSection label="Nœud">
                <InspectorRow label="ID SVG">
                  <span class="text-[var(--editor-accent)] font-mono text-[10px]">
                    {node().svgId}
                  </span>
                </InspectorRow>
                <InspectorRow label="Équipement">
                  <span
                    class="text-[var(--editor-text)] font-mono text-[10px] truncate max-w-[100px]"
                    title={node().equipmentId}
                  >
                    {node().equipmentId}
                  </span>
                </InspectorRow>
              </InspectorSection>

              {/* Transform section */}
              <InspectorSection label="Transform">
                <InspectorRow label="X">
                  <input
                    type="number"
                    value={Math.round((currentPos()?.x ?? node().x) * 10) / 10}
                    onBlur={(e) => handleXChange(e.currentTarget.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter")
                        handleXChange(e.currentTarget.value);
                    }}
                    step="1"
                    class="inspector-input w-20 bg-[var(--editor-input-bg)] border border-[var(--editor-input-border)] text-[var(--editor-text)] text-[10px] font-mono rounded px-1.5 py-0.5 text-right outline-none focus:border-[var(--editor-accent)] transition-colors"
                  />
                </InspectorRow>
                <InspectorRow label="Y">
                  <input
                    type="number"
                    value={Math.round((currentPos()?.y ?? node().y) * 10) / 10}
                    onBlur={(e) => handleYChange(e.currentTarget.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter")
                        handleYChange(e.currentTarget.value);
                    }}
                    step="1"
                    class="inspector-input w-20 bg-[var(--editor-input-bg)] border border-[var(--editor-input-border)] text-[var(--editor-text)] text-[10px] font-mono rounded px-1.5 py-0.5 text-right outline-none focus:border-[var(--editor-accent)] transition-colors"
                  />
                </InspectorRow>
              </InspectorSection>

              {/* Delta section */}
              <Show when={editorState.nodePositions[node().svgId]}>
                <InspectorSection label="Déplacement">
                  <InspectorRow label="ΔX">
                    <span
                      class={`text-[10px] font-mono ${editorState.nodePositions[node().svgId]!.x - node().x !== 0 ? "text-[var(--editor-accent)]" : "text-[var(--editor-text-muted)]"}`}
                    >
                      {(
                        editorState.nodePositions[node().svgId]!.x - node().x
                      ).toFixed(1)}
                    </span>
                  </InspectorRow>
                  <InspectorRow label="ΔY">
                    <span
                      class={`text-[10px] font-mono ${editorState.nodePositions[node().svgId]!.y - node().y !== 0 ? "text-[var(--editor-accent)]" : "text-[var(--editor-text-muted)]"}`}
                    >
                      {(
                        editorState.nodePositions[node().svgId]!.y - node().y
                      ).toFixed(1)}
                    </span>
                  </InspectorRow>
                </InspectorSection>
              </Show>
            </div>
          )}
        </Show>
      </div>

      {/* Bottom: history info */}
      <div class="px-3 py-2 border-t border-[var(--editor-border)]">
        <div class="flex items-center justify-between">
          <span class="text-[9px] text-[var(--editor-text-muted)] font-mono uppercase tracking-wider">
            Historique
          </span>
          <span class="text-[9px] text-[var(--editor-accent)] font-mono">
            {editorState.historyIndex + 1}/{editorState.history.length}
          </span>
        </div>
        <div class="mt-1 h-1 bg-[var(--editor-input-bg)] rounded-full overflow-hidden">
          <div
            class="h-full bg-[var(--editor-accent)] rounded-full transition-all"
            style={{
              width:
                editorState.history.length > 0
                  ? `${((editorState.historyIndex + 1) / editorState.history.length) * 100}%`
                  : "0%",
            }}
          />
        </div>
      </div>
    </div>
  );
};

const InspectorSection: Component<{ label: string; children: any }> = (
  props,
) => (
  <div class="mb-1">
    <div class="px-3 py-1 bg-[var(--editor-section-bg)]">
      <span class="text-[9px] uppercase tracking-widest font-bold text-[var(--editor-text-muted)] font-mono">
        {props.label}
      </span>
    </div>
    <div class="flex flex-col gap-px px-2 py-1">{props.children}</div>
  </div>
);

const InspectorRow: Component<{ label: string; children: any }> = (props) => (
  <div class="flex items-center justify-between py-0.5 min-h-6">
    <span class="text-[10px] text-[var(--editor-text-muted)] font-mono shrink-0 mr-2 w-16">
      {props.label}
    </span>
    {props.children}
  </div>
);
