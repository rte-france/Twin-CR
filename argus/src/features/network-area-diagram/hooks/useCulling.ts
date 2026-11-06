/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import * as d3 from "d3";
import type { CachedNode, CachedEdge, CachedOrphanLabel } from "../types";

export function applyCulling(
  transform: d3.ZoomTransform,
  container: HTMLElement,
  cachedNodes: CachedNode[],
  cachedEdges: CachedEdge[],
  cachedOrphanLabels: CachedOrphanLabel[],
  searchQuery: string,
  vlLayers: Record<string, boolean>,
) {
  const margin = 100 / transform.k;
  const viewLeft = -transform.x / transform.k - margin;
  const viewRight =
    (container.clientWidth - transform.x) / transform.k + margin;
  const viewTop = -transform.y / transform.k - margin;
  const viewBottom =
    (container.clientHeight - transform.y) / transform.k + margin;

  const sq = searchQuery.toLowerCase().trim();
  const isSearching = sq.length > 0;
  const showLabels = transform.k > 1.2 || isSearching;
  const hideEdges = !isSearching && transform.k < 0.2;

  for (let i = 0; i < cachedEdges.length; i++) {
    const cache = cachedEdges[i];
    if (!cache.el) continue;
    const d = cache.data;

    const isVlActive = cache.vlClass ? vlLayers[cache.vlClass] !== false : true;
    const edgeMatchesSearch =
      !isSearching ||
      d.equipmentId.toLowerCase().includes(sq) ||
      d.sourceEq.toLowerCase().includes(sq) ||
      d.targetEq.toLowerCase().includes(sq);

    const inView =
      isVlActive &&
      !hideEdges &&
      edgeMatchesSearch &&
      Math.max(d.x1, d.x2) >= viewLeft &&
      Math.min(d.x1, d.x2) <= viewRight &&
      Math.max(d.y1, d.y2) >= viewTop &&
      Math.min(d.y1, d.y2) <= viewBottom;

    if (cache.isVisible !== inView) {
      cache.el.style.visibility = inView ? "visible" : "hidden";
      cache.isVisible = inView;
    }
  }

  for (let i = 0; i < cachedNodes.length; i++) {
    const cache = cachedNodes[i];
    const isVlActive = cache.vlClass ? vlLayers[cache.vlClass] !== false : true;
    const nodeMatchesSearch =
      !isSearching || cache.data.equipmentId.toLowerCase().includes(sq);
    const inView =
      isVlActive &&
      nodeMatchesSearch &&
      cache.data.x >= viewLeft &&
      cache.data.x <= viewRight &&
      cache.data.y >= viewTop &&
      cache.data.y <= viewBottom;

    if (cache.isVisible !== inView) {
      if (cache.el) cache.el.style.visibility = inView ? "visible" : "hidden";
      cache.isVisible = inView;
    }
    const shouldShowLabels = inView && showLabels;
    if (cache.labelsVisible !== shouldShowLabels) {
      if (cache.labels)
        cache.labels.forEach(
          (l) => (l.style.visibility = shouldShowLabels ? "visible" : "hidden"),
        );
      if (cache.leaderLines)
        cache.leaderLines.forEach(
          (l) => (l.style.visibility = shouldShowLabels ? "visible" : "hidden"),
        );
      cache.labelsVisible = shouldShowLabels;
    }
  }

  for (let i = 0; i < cachedOrphanLabels.length; i++) {
    const cache = cachedOrphanLabels[i];
    const isVlActive = cache.vlClass ? vlLayers[cache.vlClass] !== false : true;
    const matchesSearch = isSearching && cache.text.toLowerCase().includes(sq);

    const shouldShow = isSearching ? matchesSearch : showLabels && isVlActive;

    if (cache.isVisible !== shouldShow) {
      cache.el.style.visibility = shouldShow ? "visible" : "hidden";
      cache.isVisible = shouldShow;
    }
  }
}
