/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { For, type Component } from "solid-js";
import { useEditorContext } from "../hooks/useEditorContext";
import type { EditTool } from "../types/editor.type";

interface ToolDef {
  id: EditTool;
  icon: string;
  label: string;
  shortcut: string;
}

const TOOLS: ToolDef[] = [
  { id: "select", icon: "◈", label: "Sélectionner", shortcut: "S" },
  { id: "move", icon: "✥", label: "Déplacer Node", shortcut: "G" },
  { id: "pan", icon: "⊕", label: "Panoramique", shortcut: "P" },
];

export const EditorToolbar: Component = () => {
  const { editorState, setTool, undo, redo, setEditorState } =
    useEditorContext();

  return (
    <div class="editor-toolbar flex flex-col gap-0.5 ml-2 my-10 shrink-0 bg-[var(--editor-toolbar-bg)] border-r border-[var(--editor-border)] py-1.5 px-1 z-30">
      {/* Tool separator */}
      <div class="text-[8px] text-[var(--editor-text-muted)] uppercase tracking-widest px-0.5 mb-0.5 font-mono">
        Outils
      </div>

      <For each={TOOLS}>
        {(tool) => (
          <button
            title={`${tool.label} (${tool.shortcut})`}
            onClick={() => setTool(tool.id)}
            class={`
              w-8 h-8 flex items-center justify-center rounded text-sm font-mono
              transition-all duration-100 relative group
              ${
                editorState.activeTool === tool.id
                  ? "bg-[var(--editor-accent)] text-[var(--editor-accent-text)] shadow-[0_0_8px_var(--editor-accent-glow)]"
                  : "text-[var(--editor-text-muted)] hover:bg-[var(--editor-hover)] hover:text-[var(--editor-text)]"
              }
            `}
          >
            {tool.icon}
            {/* Tooltip */}
            <div class="absolute left-full ml-2 top-1/2 -translate-y-1/2 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap">
              <div class="bg-[var(--editor-surface-raised)] border border-[var(--editor-border)] text-[var(--editor-text)] text-[10px] px-2 py-1 rounded font-mono shadow-lg">
                {tool.label}
                <span class="ml-2 text-[var(--editor-accent)] font-bold">
                  [{tool.shortcut}]
                </span>
              </div>
            </div>
          </button>
        )}
      </For>

      {/* Divider */}
      <div class="h-px bg-[var(--editor-border)] my-1" />

      {/* Grid options */}
      <button
        title="Grille (V)"
        onClick={() => setEditorState("showGrid", (v) => !v)}
        class={`
          w-8 h-8 flex items-center justify-center rounded text-xs font-mono
          transition-all duration-100
          ${
            editorState.showGrid
              ? "bg-[var(--editor-hover)] text-[var(--editor-text)]"
              : "text-[var(--editor-text-muted)] hover:bg-[var(--editor-hover)]"
          }
        `}
      >
        ⊞
      </button>

      <button
        title="Magnétisme Grille (M)"
        onClick={() => setEditorState("snapToGrid", (v) => !v)}
        class={`
          w-8 h-8 flex items-center justify-center rounded text-xs font-mono
          transition-all duration-100
          ${
            editorState.snapToGrid
              ? "bg-[var(--editor-accent)] text-[var(--editor-accent-text)]"
              : "text-[var(--editor-text-muted)] hover:bg-[var(--editor-hover)]"
          }
        `}
      >
        ⋈
      </button>

      {/* Divider */}
      <div class="h-px bg-[var(--editor-border)] my-1 mt-auto" />

      {/* Undo / Redo */}
      <button
        title="Annuler (Ctrl+Z)"
        onClick={undo}
        disabled={editorState.historyIndex < 0}
        class="w-8 h-8 flex items-center justify-center rounded text-xs font-mono text-[var(--editor-text-muted)] hover:bg-[var(--editor-hover)] hover:text-[var(--editor-text)] disabled:opacity-30 transition-all"
      >
        ↩
      </button>
      <button
        title="Rétablir (Ctrl+Y)"
        onClick={redo}
        disabled={editorState.historyIndex >= editorState.history.length - 1}
        class="w-8 h-8 flex items-center justify-center rounded text-xs font-mono text-[var(--editor-text-muted)] hover:bg-[var(--editor-hover)] hover:text-[var(--editor-text)] disabled:opacity-30 transition-all"
      >
        ↪
      </button>
    </div>
  );
};
