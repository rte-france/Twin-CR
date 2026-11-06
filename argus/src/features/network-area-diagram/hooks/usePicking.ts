/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import * as d3 from "d3";
import { NadNode, PickInfo, RenderEdge } from "../types";

const distSq = (
  p: { x: number; y: number },
  v: { x: number; y: number },
  w: { x: number; y: number },
) => {
  const l2 = (w.x - v.x) ** 2 + (w.y - v.y) ** 2;
  if (l2 === 0) return (p.x - v.x) ** 2 + (p.y - v.y) ** 2;
  let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
  return (
    (p.x - (v.x + Math.max(0, Math.min(1, t)) * (w.x - v.x))) ** 2 +
    (p.y - (v.y + Math.max(0, Math.min(1, t)) * (w.y - v.y))) ** 2
  );
};

export function getPickInfo(
  clientX: number,
  clientY: number,
  transform: d3.ZoomTransform,
  overlayRect: DOMRect,
  quadtree: d3.Quadtree<NadNode>,
  edgesData: RenderEdge[],
  searchQuery: string,
): PickInfo | null {
  const wx = (clientX - overlayRect.left - transform.x) / transform.k;
  const wy = (clientY - overlayRect.top - transform.y) / transform.k;
  const searchRadius = 15 / transform.k;
  const sq = searchQuery.toLowerCase().trim();

  const node = quadtree.find(wx, wy, searchRadius);
  if (node && (!sq || node.equipmentId.toLowerCase().includes(sq))) {
    return {
      svgId: node.svgId,
      equipmentId: node.equipmentId,
      elementType: "node",
      label: node.equipmentId,
    };
  }

  const sqRadius = searchRadius * searchRadius;
  for (let i = 0; i < edgesData.length; i++) {
    const e = edgesData[i];
    if (
      sq &&
      !e.equipmentId.toLowerCase().includes(sq) &&
      !e.sourceEq.toLowerCase().includes(sq) &&
      !e.targetEq.toLowerCase().includes(sq)
    )
      continue;
    if (
      distSq({ x: wx, y: wy }, { x: e.x1, y: e.y1 }, { x: e.x2, y: e.y2 }) <
      sqRadius
    ) {
      return {
        svgId: e.svgId,
        equipmentId: e.equipmentId,
        elementType: "edge",
        label: e.equipmentId,
      };
    }
  }
  return null;
}
