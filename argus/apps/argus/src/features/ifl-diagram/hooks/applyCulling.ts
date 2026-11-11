/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export function applyCulling(
  transform: d3.ZoomTransform,
  container: HTMLElement,
  searchQuery: string,
  svg: SVGSVGElement,
) {
  const margin = 100 / transform.k;
  const viewLeft = -transform.x / transform.k - margin;
  const viewRight = (container.clientWidth - transform.x) / transform.k + margin;
  const viewTop = -transform.y / transform.k - margin;
  const viewBottom = (container.clientHeight - transform.y) / transform.k + margin;

  const sq = searchQuery.toLowerCase().trim();
  const isSearching = sq.length > 0;

  function inView(x: number, y: number): boolean {
    return x >= viewLeft && x <= viewRight && y >= viewTop && y <= viewBottom;
  }

  function matchesSearch(id: string): boolean {
    return id.toLowerCase().includes(sq);
  }

  // Nodes (circles and rects)
  svg.querySelectorAll<SVGElement>("circle[data-node], rect[data-node]").forEach(el => {
    const id = el.dataset.node ?? "";
    const cx = parseFloat(el.getAttribute("cx") ?? el.getAttribute("x") ?? "0");
    const cy = parseFloat(el.getAttribute("cy") ?? el.getAttribute("y") ?? "0");
    const visible = inView(cx, cy) && (!isSearching || matchesSearch(id));
    el.style.display = visible ? "" : "none";
  });

  // Labels (text elements)
  svg.querySelectorAll<SVGTextElement>("text").forEach(el => {
    const id = el.textContent ?? "";
    const x = parseFloat(el.getAttribute("x") ?? "0");
    const y = parseFloat(el.getAttribute("y") ?? "0");
    const inFrame = inView(x, y);
    el.setAttribute("display", inFrame && (!isSearching || matchesSearch(id)) ? "block" : "none");
  });

  // Links (lines)
  svg.querySelectorAll<SVGLineElement>("line[data-from]").forEach(el => {
    const from = el.dataset.from ?? "";
    const to = el.dataset.to ?? "";
    const x1 = parseFloat(el.getAttribute("x1") ?? "0");
    const y1 = parseFloat(el.getAttribute("y1") ?? "0");
    const x2 = parseFloat(el.getAttribute("x2") ?? "0");
    const y2 = parseFloat(el.getAttribute("y2") ?? "0");
    // Show link if either endpoint is in view
    const visible = (inView(x1, y1) || inView(x2, y2))
      && (!isSearching || matchesSearch(from) || matchesSearch(to));
    el.style.display = visible ? "" : "none";
  });
}
