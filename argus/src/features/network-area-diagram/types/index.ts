/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export { NadContext } from "./nad-context.type";
export type { NadContextType } from "./nad-context.type";

export interface NadNode {
  svgId: string;
  equipmentId: string;
  x: number;
  y: number;
}
export interface NadEdge {
  svgId: string;
  equipmentId?: string;
  source?: string;
  target?: string;
  node1?: string;
  node2?: string;
}
export interface NadMetadata {
  nodes: NadNode[];
  edges: NadEdge[];
}
export interface NadResponse {
  success: boolean;
  svg_content: string;
  metadata: NadMetadata;
  error?: string;
}
export interface PickInfo {
  svgId: string;
  equipmentId: string;
  elementType: "node" | "edge";
  label: string;
}

export interface EquipmentLayer {
  generator: boolean;
  load: boolean;
  battery: boolean;
  capacitor: boolean;
  inductor: boolean;
  svc: boolean;
};

export interface RenderEdge {
  svgId: string;
  equipmentId: string;
  sourceEq: string;
  targetEq: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface CachedNode {
  data: NadNode;
  el: SVGElement | null;
  labels: (HTMLElement | SVGElement)[] | null;
  leaderLines: SVGElement[] | null;
  vlClass: string | null;
  isVisible: boolean;
  labelsVisible: boolean;
}

export interface CachedEdge {
  data: RenderEdge;
  el: SVGElement | null;
  vlClass: string | null;
  isVisible: boolean;
}

export interface CachedOrphanLabel {
  el: HTMLElement | SVGElement;
  text: string;
  vlClass: string | null;
  isVisible: boolean;
}

export const VL_COLORS: Record<string, { label: string; color: string }> = {
  "nad-vl300to500": { label: "300-500 kV", color: "#d32f2f" },
  "nad-vl180to300": { label: "180-300 kV", color: "#2e7d32" },
  "nad-vl120to180": { label: "120-180 kV", color: "#00ACC1" },
  "nad-vl70to120": { label: "70-120 kV", color: "#e65100" },
  "nad-vl50to70": { label: "50-70 kV", color: "#9c27b0" },
  "nad-vl30to50": { label: "30-50 kV", color: "#ef9a9a" },
  "nad-vl0to30": { label: "0-30 kV", color: "#afb42b" },
};

export interface Nad {
  id: string;
  name: string;
  params: {
    vlIds: string[];
    depth: number;
    layout: "default" | "geographical";
    radiusFactor: number;
    layers: { labels: boolean; edgeInfos: boolean; injections: boolean };
    equipmentLayers: EquipmentLayer;
    flowType: "active" | "reactive" | "current";
    layoutMode: "default" | "manhattan" | "octolinear";
  };
}

export function createDefaultNad(id: string, name: string): Nad {
  return {
    id,
    name,
    params: {
      vlIds: [],
      depth: 0,
      layout: "default",
      radiusFactor: 500,
      layers: { labels: true, edgeInfos: true, injections: true },
      equipmentLayers: { generator: true, load: true, battery: true, capacitor: true, inductor: true, svc: true },
      flowType: "active",
      layoutMode: "default",
    },
  };
}
