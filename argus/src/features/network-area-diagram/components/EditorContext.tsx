/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createStore, produce } from "solid-js/store";
import { ParentComponent } from "solid-js";
import {
  EditorContext,
  EditorContextType,
  EditorState,
  EditTool,
  HistoryEntry,
} from "../types/editor.type";

const MAX_HISTORY = 50;

export const EditorProvider: ParentComponent = (props) => {
  const [editorState, setEditorState] = createStore<EditorState>({
    isEditing: false,
    activeTool: "select",
    selectedNodeId: null,
    hoveredNodeId: null,
    isDragging: false,
    showGrid: true,
    snapToGrid: false,
    gridSize: 50,
    nodePositions: {},
    history: [],
    historyIndex: -1,
  });

  const toggleEditing = () => {
    setEditorState("isEditing", (v) => !v);
    if (editorState.isEditing) {
      // Leaving edit mode — clear selection
      setEditorState("selectedNodeId", null);
    }
  };

  const setTool = (tool: EditTool) => {
    setEditorState("activeTool", tool);
  };

  const selectNode = (id: string | null) => {
    setEditorState("selectedNodeId", id);
  };

  const moveNode = (id: string, x: number, y: number) => {
    const snapped = editorState.snapToGrid
      ? {
          x: Math.round(x / editorState.gridSize) * editorState.gridSize,
          y: Math.round(y / editorState.gridSize) * editorState.gridSize,
        }
      : { x, y };
    setEditorState("nodePositions", id, snapped);
  };

  const commitMove = (id: string, prevX: number, prevY: number) => {
    const current = editorState.nodePositions[id];
    if (!current) return;
    const entry: HistoryEntry = {
      type: "move",
      nodeId: id,
      prevX,
      prevY,
      nextX: current.x,
      nextY: current.y,
    };
    setEditorState(
      produce((s) => {
        // Trim future if we're not at end
        s.history = s.history.slice(0, s.historyIndex + 1);
        s.history.push(entry);
        if (s.history.length > MAX_HISTORY) s.history.shift();
        s.historyIndex = s.history.length - 1;
      }),
    );
  };

  const undo = () => {
    if (editorState.historyIndex < 0) return;
    const entry = editorState.history[editorState.historyIndex];
    if (entry.type === "move") {
      setEditorState("nodePositions", entry.nodeId, {
        x: entry.prevX,
        y: entry.prevY,
      });
    }
    setEditorState("historyIndex", (i) => i - 1);
  };

  const redo = () => {
    if (editorState.historyIndex >= editorState.history.length - 1) return;
    const entry = editorState.history[editorState.historyIndex + 1];
    if (entry.type === "move") {
      setEditorState("nodePositions", entry.nodeId, {
        x: entry.nextX,
        y: entry.nextY,
      });
    }
    setEditorState("historyIndex", (i) => i + 1);
  };

  const resetNodePositions = () => {
    setEditorState("nodePositions", {});
    setEditorState("history", []);
    setEditorState("historyIndex", -1);
  };

  const ctx: EditorContextType = {
    editorState,
    setEditorState,
    toggleEditing,
    setTool,
    selectNode,
    moveNode,
    commitMove,
    undo,
    redo,
    resetNodePositions,
  };

  return (
    <EditorContext.Provider value={ctx}>
      {props.children}
    </EditorContext.Provider>
  );
};
