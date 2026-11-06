/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export { IflContext } from "./ifl-context.type";
export type { IflContextType } from "./ifl-context.type";

export interface IflNode {
  svgId: string;
  equipmentId: string;
  x: number;
  y: number;
}
export interface IflEdge {
  svgId: string;
  equipmentId?: string;
  source?: string;
  target?: string;
  node1?: string;
  node2?: string;
}

export type IflResponse =
  | { success: true; svg_content: string }
  | { success: false; error: string };

export type PickInfo =
  | { elementType: "node"; nodeId: string }
  | { elementType: "edge"; from: string; to: string };

export interface IflParams {
  id: string;
  name: string;
  nodeIds: string[];
  depth: number;
}
