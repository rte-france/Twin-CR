/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  Component,
  createEffect,
  onCleanup,
  Show,
} from "solid-js";
import * as d3 from "d3";
import { useIflContext } from "../hooks/useIflContext";
import { applyCulling } from "../hooks/applyCulling";
import { d3Zoom } from "../../network-area-diagram/directives/d3Zoom";
import { IflTooltip } from "./IflTooltip";

false && d3Zoom;

export const IflCanvas: Component = () => {
  const ctx = useIflContext();

  let containerRef!: HTMLDivElement;
  let svgWrapRef!: HTMLDivElement;

  let currentTransform = d3.zoomIdentity;
  let cullingRafId: number | null = null;
  let lastProcessedSvg = "";

  function getSvgEl(): SVGSVGElement | null {
    return svgWrapRef?.querySelector("svg") ?? null;
  }

  function applyZoom(svgEl: SVGSVGElement, k: number) {
    // Scale node sizes inversely so they appear constant
    svgEl.querySelectorAll<SVGCircleElement>("circle").forEach(el => {
      const base = el.getAttribute("base_r") ?? el.getAttribute("r");
      if (base) el.setAttribute("r", String(parseFloat(base) / k));
    });
    svgEl.querySelectorAll<SVGRectElement>("rect").forEach(el => {
      const base = el.getAttribute("base_r");
      if (base) {
        const size = parseFloat(base) * 2 / k;
        const cx = parseFloat(el.getAttribute("cx") ?? "0");
        const cy = parseFloat(el.getAttribute("cy") ?? "0");
        el.setAttribute("width",  String(size));
        el.setAttribute("height", String(size));
        el.setAttribute("x", String(cx - size / 2));
        el.setAttribute("y", String(cy - size / 2));
      }
    });

    const fontSize = 14 / k;
    const textColor = "gray";  // TODO: make theme-dependent
    svgEl.querySelectorAll<SVGTextElement>("text").forEach(el => {
      el.setAttribute("font-size", String(fontSize));
      el.setAttribute("fill", textColor);
    });

    // Scale line thickness inversely so it appears constant at 1px
    svgEl.querySelectorAll<SVGLineElement>("line").forEach(el => {
      el.setAttribute("stroke-width", String(2 / k));
    });
  }

  function applyTransform(t: d3.ZoomTransform) {
    const svgEl = getSvgEl();
    if (!svgEl) return;
    let g = svgEl.querySelector<SVGGElement>("g.zoom-layer");
    if (!g) {
      g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.classList.add("zoom-layer");
      while (svgEl.firstChild) g.appendChild(svgEl.firstChild);
      svgEl.appendChild(g);
    }
    g.setAttribute("transform", `translate(${t.x}, ${t.y}) scale(${t.k})`);
    applyZoom(svgEl, t.k);
  }

  function scheduleCulling() {
    const svgEl = getSvgEl();
    if (!containerRef || !svgEl) return;
    applyCulling(currentTransform, containerRef, ctx.searchQuery(), svgEl);
  }

  function getNodeExtents() {
    const nodes = Array.from(
      svgWrapRef.querySelectorAll<SVGElement>("circle[data-node], rect[data-node]")
    ).map((el) => ({
      x: parseFloat(el.getAttribute("cx") ?? el.getAttribute("x") ?? "0"),
      y: parseFloat(el.getAttribute("cy") ?? el.getAttribute("y") ?? "0"),
    }));
    if (!nodes.length) return null;
    return {
      xEx: d3.extent(nodes, (d) => d.x) as [number, number],
      yEx: d3.extent(nodes, (d) => d.y) as [number, number],
    };
  }

  createEffect(() => {
    const data = ctx.iflData();
    if (!data?.success) return;

    const isNewSvg = lastProcessedSvg !== data.svg_content;
    lastProcessedSvg = data.svg_content;

    svgWrapRef.innerHTML = data.svg_content;
    const svgEl = getSvgEl();
    if (svgEl) {
      svgEl.removeAttribute("viewBox");
      svgEl.removeAttribute("width");
      svgEl.removeAttribute("height");
      svgEl.style.cssText =
        "width: 100%; height: 100%; pointer-events: none; overflow: visible; content-visibility: visible;";
    }

    if (isNewSvg) {
      ctx.setFitCanvas(() => () => {
        const extents = getNodeExtents();
        if (!extents || !containerRef) return;
        ctx.fitEngine?.(extents.xEx, extents.yEx, containerRef.clientWidth, containerRef.clientHeight);
      });
      ctx.fitCanvas()();
    } else {
      applyTransform(currentTransform);
      scheduleCulling();
    }
  });

  // Re-run culling when search query changes
  createEffect(() => {
    ctx.searchQuery();
    if (ctx.iflData()) scheduleCulling();
  });

  onCleanup(() => {
    if (cullingRafId !== null) cancelAnimationFrame(cullingRafId);
  });

  return (
    <div class="flex-1 relative overflow-hidden bg-background flex flex-col">
      <style>{`
        .layer-hide-labels .ifl-text-nodes, .layer-hide-labels .ifl-text-edges { visibility: hidden !important; }
      `}</style>

      <div class="flex flex-1 overflow-hidden relative">
        <div
          ref={containerRef}
          class="relative flex-1 overflow-hidden cursor-grab active:cursor-grabbing"
        >
          <div
            ref={svgWrapRef}
            classList={{
              "layer-hide-labels": !ctx.layers.labels,
            }}
            class="absolute inset-0"
            use:d3Zoom={{
              onZoom: (t: d3.ZoomTransform) => {
                currentTransform = t;
                applyTransform(t);
                scheduleCulling();
              },
              onRightClick: (e: MouseEvent) => {
                const svgEl = getSvgEl();
                if (!svgEl) return;

                // Convert screen coords to SVG space
                const rect = containerRef.getBoundingClientRect();
                const x = (e.clientX - rect.left - currentTransform.x) / currentTransform.k;
                const y = (e.clientY - rect.top - currentTransform.y) / currentTransform.k;

                // Check nodes first (circles and rects)
                for (const el of svgEl.querySelectorAll<SVGElement>("circle[data-node], rect[data-node]")) {
                  if (el.style.display === "none") continue;
                  const cx = parseFloat(el.getAttribute("cx") ?? el.getAttribute("x") ?? "0");
                  const cy = parseFloat(el.getAttribute("cy") ?? el.getAttribute("y") ?? "0");
                  const r = parseFloat(el.getAttribute("r") ?? el.getAttribute("width") ?? "0");
                  if (Math.hypot(x - cx, y - cy) <= r) {
                    ctx.setSelected({ elementType: "node", nodeId: el.dataset.node! });
                    return;
                  }
                }

                // Check edges (lines)
                for (const el of svgEl.querySelectorAll<SVGLineElement>("line[data-from]")) {
                  if (el.style.display === "none") continue;
                  const x1 = parseFloat(el.getAttribute("x1") ?? "0");
                  const y1 = parseFloat(el.getAttribute("y1") ?? "0");
                  const x2 = parseFloat(el.getAttribute("x2") ?? "0");
                  const y2 = parseFloat(el.getAttribute("y2") ?? "0");
                  if (distanceToSegment(x, y, x1, y1, x2, y2) <= 5 / currentTransform.k) {
                    ctx.setSelected({ elementType: "edge", from: el.dataset.from!, to: el.dataset.to! });
                    return;
                  }
                }

                ctx.setSelected(null);
              },
              registerFit: (fn: any) => { ctx.fitEngine = fn; },
            }}
          />

          <Show when={ctx.iflData.loading}>
            <div class="absolute inset-0 bg-overlay backdrop-blur-sm grid place-content-center z-20 text-text-on-accent tracking-widest font-bold">
              Loading network...
            </div>
          </Show>

          <IflTooltip />
        </div>
      </div>
    </div>
  );
};

function distanceToSegment(
  px: number, py: number,
  x1: number, y1: number,
  x2: number, y2: number,
): number {
  const dx = x2 - x1, dy = y2 - y1;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(px - x1, py - y1);
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lenSq));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}
