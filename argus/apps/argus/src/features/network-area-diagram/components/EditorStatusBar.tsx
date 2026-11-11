/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, createMemo } from "solid-js";
import { useEditorContext } from "../hooks/useEditorContext";

export const EditorStatusBar: Component = () => {
  const { editorState, resetNodePositions } = useEditorContext();

  const toolLabels: Record<string, string> = {
    select: "SÉLECTIONNER  •  Clic droit sur un nœud pour le sélectionner",
    move: "DÉPLACER  •  Clic gauche + glisser sur un nœud pour le déplacer",
    pan: "PANORAMIQUE  •  Clic gauche + glisser pour naviguer",
    connect: "CONNEXION  •  Clic sur source puis destination",
  };

  const modifiedCount = createMemo(
    () => Object.keys(editorState.nodePositions).length,
  );

  return (
    <div class="editor-statusbar h-6 shrink-0 bg-[var(--editor-statusbar-bg)] border-t border-[var(--editor-border)] flex items-center px-3  gap-4 font-mono text-[9px] overflow-hidden">
      {/* Mode indicator */}
      <div class="flex items-center gap-1.5">
        <span class="w-1.5 h-1.5 rounded-full bg-[var(--editor-accent)] animate-pulse" />
        <span class="text-[var(--editor-accent)] font-bold uppercase tracking-widest">
          MODE ÉDITION
        </span>
      </div>

      <div class="w-px h-3 bg-[var(--editor-border)]" />

      {/* Active tool hint */}
      <span class="text-[var(--editor-text-muted)] truncate">
        {toolLabels[editorState.activeTool]}
      </span>

      <div class="flex-1" />

      {/* Modified nodes count */}
      {modifiedCount() > 0 && (
        <>
          <div class="w-px h-3 bg-[var(--editor-border)]" />
          <span class="text-[var(--editor-warning)]">
            {modifiedCount()} nœud{modifiedCount() > 1 ? "s" : ""} modifié
            {modifiedCount() > 1 ? "s" : ""}
          </span>
          <button
            onClick={resetNodePositions}
            class="text-[var(--editor-text-muted)] hover:text-[var(--editor-danger)] transition-colors"
            title="Réinitialiser toutes les positions"
          >
            ✕ Réinitialiser
          </button>
        </>
      )}

      <div class="w-px h-3 bg-[var(--editor-border)]" />

      {/* Shortcuts reminder */}
      <span class="text-[var(--editor-text-muted)] opacity-60">
        <span class="text-[var(--editor-text)]">S</span> Sél.{" "}
        <span class="text-[var(--editor-text)]">G</span> Dépl.{" "}
        <span class="text-[var(--editor-text)]">Ctrl+Z</span> Annul.{" "}
        <span class="text-[var(--editor-text)]">Esc</span> Quitter éd.
      </span>
    </div>
  );
};
