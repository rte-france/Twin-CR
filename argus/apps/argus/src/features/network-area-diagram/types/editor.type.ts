/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createContext } from "solid-js";
import { SetStoreFunction } from "solid-js/store";

export type EditTool = "select" | "move" | "pan" | "connect";

export interface EditorNode {
  svgId: string;
  equipmentId: string;
  x: number;
  y: number;
  isDirty?: boolean;
}

export interface EditorState {
  isEditing: boolean;
  activeTool: EditTool;
  selectedNodeId: string | null;
  hoveredNodeId: string | null;
  isDragging: boolean;
  showGrid: boolean;
  snapToGrid: boolean;
  gridSize: number;
  nodePositions: Record<string, { x: number; y: number }>;
  history: HistoryEntry[];
  historyIndex: number;
}

export interface HistoryEntry {
  type: "move";
  nodeId: string;
  prevX: number;
  prevY: number;
  nextX: number;
  nextY: number;
}

export interface EditorContextType {
  editorState: EditorState;
  setEditorState: SetStoreFunction<EditorState>;
  toggleEditing: () => void;
  setTool: (tool: EditTool) => void;
  selectNode: (id: string | null) => void;
  moveNode: (id: string, x: number, y: number) => void;
  commitMove: (id: string, prevX: number, prevY: number) => void;
  undo: () => void;
  redo: () => void;
  resetNodePositions: () => void;
}

export const EditorContext = createContext<EditorContextType>();
