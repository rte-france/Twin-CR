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
  createSignal,
} from "solid-js";
import { unwrap } from "solid-js/store";
import * as d3 from "d3";
import { useNadContext } from "../hooks/useNadContext";
import { applyCulling } from "../hooks/useCulling";
import { getPickInfo } from "../hooks/usePicking";
import { d3Zoom } from "../directives/d3Zoom";
import {
  CachedNode,
  CachedEdge,
  CachedOrphanLabel,
  NadNode,
  RenderEdge,
  VL_COLORS,
} from "../types";
import { NadTooltip } from "./NadTooltip";
import { EditorOverlay } from "../components/EditorOverlay";
import { EditorToolbar } from "../components/EditorToolbar";
import { EditorInspector } from "../components/EditorInspector";
import { EditorStatusBar } from "../components/EditorStatusBar";
import { useEditorContext } from "../hooks/useEditorContext";

false && d3Zoom;

export const NadCanvas: Component = () => {
  const ctx = useNadContext();
  const editor = useEditorContext();

  let containerRef!: HTMLDivElement;
  let svgWrapRef!: HTMLDivElement;
  let overlayRef!: HTMLDivElement;

  let nodesData: NadNode[] = [];
  let edgesData: RenderEdge[] = [];
  let cachedNodes: CachedNode[] = [];
  let cachedEdges: CachedEdge[] = [];
  let cachedOrphanLabels: CachedOrphanLabel[] = [];
  let quadtree: d3.Quadtree<NadNode>;
  let currentTransform = d3.zoomIdentity;
  let cullingRafId: number | null = null;
  let fitEngine: any;
  let lastProcessedSvg = "";

  const [transform, setTransform] = createSignal<d3.ZoomTransform>(
    d3.zoomIdentity,
  );

  createEffect(() => {
    if (ctx.vlIds().length > 0 && ctx.status() === "idle") ctx.triggerLoad();
  });

  createEffect(() => {
    const data = ctx.nadData();
    const layout = ctx.layoutMode();
    if (!data) return;

    const isNewData = lastProcessedSvg !== data.svg_content;
    lastProcessedSvg = data.svg_content;

    svgWrapRef.innerHTML = data.svg_content;
    const svgEl = svgWrapRef.querySelector("svg");

    if (svgEl) {
      svgEl.removeAttribute("viewBox");
      svgEl.removeAttribute("width");
      svgEl.removeAttribute("height");
      svgEl.style.cssText =
        "width: 100%; height: 100%; pointer-events: none; overflow: visible; content-visibility: visible;";
      svgEl.querySelectorAll("foreignObject > div").forEach((el) => {
        (el as HTMLElement).style.cssText =
          "position: relative; width: 100%; height: 100%;";
      });

      if (layout !== "default") {
        const manhattanLine = d3
          .line<[number, number]>()
          .x((d) => d[0])
          .y((d) => d[1])
          .curve(d3.curveStep);
        const generateTubePath = (points: [number, number][]) => {
          if (points.length < 2) return "";
          let d = `M ${points[0][0]},${points[0][1]}`;
          for (let i = 0; i < points.length - 1; i++) {
            const [x1, y1] = points[i];
            const [x2, y2] = points[i + 1];
            const dx = x2 - x1;
            const dy = y2 - y1;
            const absDx = Math.abs(dx);
            const absDy = Math.abs(dy);
            const signX = Math.sign(dx);
            const signY = Math.sign(dy);

            if (absDx > absDy) {
              const straight = (absDx - absDy) / 2;
              d += ` L ${x1 + signX * straight},${y1} L ${x2 - signX * straight},${y2} L ${x2},${y2}`;
            } else {
              const straight = (absDy - absDx) / 2;
              d += ` L ${x1},${y1 + signY * straight} L ${x2},${y2 - signY * straight} L ${x2},${y2}`;
            }
          }
          return d;
        };

        d3.select(svgWrapRef)
          .selectAll(".nad-edge-path")
          .each(function () {
            const el = d3.select(this);
            if ((this as Element).nodeName.toLowerCase() === "polyline") {
              const pointsStr = el.attr("points");
              if (!pointsStr) return;
              const points = pointsStr
                .trim()
                .split(/\s+/)
                .map((p) => {
                  const coords = p.split(",");
                  return [parseFloat(coords[0]), parseFloat(coords[1])] as [
                    number,
                    number,
                  ];
                });

              const pathData =
                layout === "manhattan"
                  ? manhattanLine(points)
                  : generateTubePath(points);
              if (pathData) {
                const parent = d3.select(
                  (this as Element).parentNode as Element,
                );
                parent
                  .insert("path", () => this as Element)
                  .attr("class", el.attr("class"))
                  .attr("d", pathData);
                el.remove();
              }
            }
          });
      }
    }

    nodesData = data.metadata.nodes;
    const nodeMap = new Map(nodesData.map((n) => [n.svgId, n]));

    edgesData = data.metadata.edges.reduce((acc, edge) => {
      const sId = edge.source || edge.node1;
      const tId = edge.target || edge.node2;
      if (!sId || !tId) return acc;
      const s = nodeMap.get(sId);
      const t = nodeMap.get(tId);
      if (s && t)
        acc.push({
          svgId: edge.svgId,
          equipmentId: edge.equipmentId || edge.svgId,
          sourceEq: s.equipmentId,
          targetEq: t.equipmentId,
          x1: s.x,
          y1: s.y,
          x2: t.x,
          y2: t.y,
        });
      return acc;
    }, [] as RenderEdge[]);

    const mappedIds = new Set<string>();

    cachedNodes = nodesData.map((n) => {
      const safeId = n.svgId.replace(/"/g, '\\"');
      const domEl = svgWrapRef.querySelector(
        `[id="${safeId}"]`,
      ) as SVGElement | null;
      const externalLabel = svgWrapRef.querySelector(
        `[id="${safeId}-textnode"]`,
      ) as HTMLElement | null;
      const leaderLine = svgWrapRef.querySelector(
        `[id="${safeId}-textedge"]`,
      ) as SVGElement | null;

      if (externalLabel) mappedIds.add(externalLabel.id);
      if (leaderLine) mappedIds.add(leaderLine.id);

      const labels: (HTMLElement | SVGElement)[] = [];
      if (externalLabel) labels.push(externalLabel);
      if (domEl)
        domEl
          .querySelectorAll("foreignObject, text")
          .forEach((l) => labels.push(l as SVGElement));

      let vlClass = null;
      if (domEl) {
        const circle = domEl.querySelector("circle");
        if (circle)
          vlClass =
            Array.from(circle.classList).find((c) => c.startsWith("nad-vl")) ||
            null;
      }
      return {
        data: n,
        el: domEl,
        labels: labels.length ? labels : null,
        leaderLines: leaderLine ? [leaderLine] : null,
        vlClass,
        isVisible: true,
        labelsVisible: true,
      };
    });

    cachedEdges = edgesData.map((e) => {
      const safeId = e.svgId.replace(/"/g, '\\"');
      const domEl = svgWrapRef.querySelector(
        `[id="${safeId}"]`,
      ) as SVGElement | null;
      let vlClass = null;
      if (domEl) {
        const childWithVl = domEl.querySelector('[class*="nad-vl"]');
        if (childWithVl)
          vlClass =
            Array.from(childWithVl.classList).find((c) =>
              c.startsWith("nad-vl"),
            ) || null;
      }
      return { data: e, el: domEl, vlClass, isVisible: true };
    });

    const orphans: CachedOrphanLabel[] = [];
    svgWrapRef
      .querySelectorAll(".nad-label-box, .nad-text-edges polyline")
      .forEach((el) => {
        if (!mappedIds.has(el.id)) {
          let vlClass = null;
          const legendSquare = el.querySelector(".nad-legend-square");
          if (legendSquare)
            vlClass =
              Array.from(legendSquare.classList).find((c) =>
                c.startsWith("nad-vl"),
              ) || null;
          orphans.push({
            el: el as HTMLElement | SVGElement,
            text: el.textContent || "",
            vlClass,
            isVisible: true,
          });
        }
      });
    cachedOrphanLabels = orphans;

    quadtree = d3
      .quadtree<NadNode>()
      .x((d) => d.x)
      .y((d) => d.y)
      .addAll(nodesData);

    if (isNewData) {
      ctx.setFitCanvas(() => () => {
        // GARDE FOU CRITIQUE ICI : Ne s'exécute que si containerRef existe
        if (!containerRef) return;
        const xEx = d3.extent(nodesData, (d) => d.x) as [number, number];
        const yEx = d3.extent(nodesData, (d) => d.y) as [number, number];
        if (fitEngine)
          fitEngine(
            xEx,
            yEx,
            containerRef.clientWidth,
            containerRef.clientHeight,
          );
      });
      ctx.fitCanvas()();
    } else {
      svgWrapRef.style.transform = `translate(${currentTransform.x}px, ${currentTransform.y}px) scale(${currentTransform.k})`;
      if (cullingRafId !== null) cancelAnimationFrame(cullingRafId);
      cullingRafId = requestAnimationFrame(() => {
        // GARDE FOU CRITIQUE ICI
        if (!containerRef) return;
        applyCulling(
          currentTransform,
          containerRef,
          cachedNodes,
          cachedEdges,
          cachedOrphanLabels,
          ctx.searchQuery(),
          ctx.vlLayers,
        );
      });
    }
  });

  createEffect(() => {
    ctx.searchQuery();
    JSON.stringify(unwrap(ctx.vlLayers));
    if (ctx.nadData()) {
      if (cullingRafId !== null) cancelAnimationFrame(cullingRafId);
      cullingRafId = requestAnimationFrame(() => {
        // GARDE FOU CRITIQUE ICI
        if (!containerRef) return;
        applyCulling(
          currentTransform,
          containerRef,
          cachedNodes,
          cachedEdges,
          cachedOrphanLabels,
          ctx.searchQuery(),
          ctx.vlLayers,
        );
      });
    }
  });

  onCleanup(() => {
    if (cullingRafId !== null) cancelAnimationFrame(cullingRafId);
  });

  const isEditorPanDisabled = () =>
    editor.editorState.isEditing &&
    (editor.editorState.activeTool === "move" ||
      editor.editorState.activeTool === "select");

  return (
    <div
      class={`flex-1 relative overflow-hidden bg-background flex flex-col ${editor.editorState.isEditing ? "nad-editing-mode" : ""}`}
    >
      <style>{`
          .layer-hide-labels .nad-text-nodes, .layer-hide-labels .nad-text-edges { visibility: hidden !important; }
          .layer-hide-edge-infos .nad-edge-infos { visibility: hidden !important; }
          .layer-hide-injections .nad-injections { visibility: hidden !important; }

          ${Object.keys(VL_COLORS)
            .map((vl) =>
              !ctx.vlLayers[vl]
                ? `.${vl} { visibility: hidden !important; }`
                : "",
            )
            .join("\n")}
          ${!ctx.equipmentLayers.generator ? ".nad-generator { visibility: hidden !important; }" : ""}
          ${!ctx.equipmentLayers.load ? ".nad-load { visibility: hidden !important; }" : ""}
          ${!ctx.equipmentLayers.battery ? ".nad-battery { visibility: hidden !important; }" : ""}
          ${!ctx.equipmentLayers.capacitor ? ".nad-capacitor, .nad-inductor, .nad-svc { visibility: hidden !important; }" : ""}

          ${ctx.flowType() !== "active" ? ".nad-active { visibility: hidden !important; }" : ""}
          ${ctx.flowType() !== "reactive" ? ".nad-reactive { visibility: hidden !important; }" : ""}
          ${ctx.flowType() !== "current" ? ".nad-current { visibility: hidden !important; }" : ""}
          ${ctx.hideDisconnected() ? ".nad-disconnected { visibility: hidden !important; }" : ""}
        `}</style>

      <div class="flex flex-1 overflow-hidden relative editor-layout nad-canvas-container">
        <Show when={editor.editorState.isEditing}>
          <EditorToolbar />
        </Show>

        <div class="relative flex-1 overflow-hidden" ref={containerRef}>
          <div
            ref={svgWrapRef}
            classList={{
              "layer-hide-labels": !ctx.layers.labels,
              "layer-hide-edge-infos": !ctx.layers.edgeInfos,
              "layer-hide-injections": !ctx.layers.injections,
            }}
            class="absolute inset-0 origin-top-left will-change-transform"
          />

          <Show when={editor.editorState.isEditing && ctx.nadData()}>
            <EditorOverlay transform={transform} containerRef={containerRef!} />
          </Show>

          <div
            ref={overlayRef}
            use:d3Zoom={{
              onZoom: (t: d3.ZoomTransform) => {
                currentTransform = t;
                setTransform(t);
                if (svgWrapRef) {
                  svgWrapRef.style.transform = `translate(${t.x}px, ${t.y}px) scale(${t.k})`;
                }
                if (cullingRafId !== null) cancelAnimationFrame(cullingRafId);
                cullingRafId = requestAnimationFrame(() => {
                  // GARDE FOU CRITIQUE ICI
                  if (!containerRef) return;
                  applyCulling(
                    t,
                    containerRef,
                    cachedNodes,
                    cachedEdges,
                    cachedOrphanLabels,
                    ctx.searchQuery(),
                    ctx.vlLayers,
                  );
                });
              },
              onRightClick: (e: MouseEvent) => {
                ctx.setSelected(
                  getPickInfo(
                    e.clientX,
                    e.clientY,
                    currentTransform,
                    overlayRef.getBoundingClientRect(),
                    quadtree,
                    edgesData,
                    ctx.searchQuery(),
                  ),
                );
              },
              registerFit: (fn: any) => {
                fitEngine = fn;
              },
              panDisabled: isEditorPanDisabled,
            }}
            class={`absolute inset-0 z-10 ${
              editor.editorState.isEditing
                ? editor.editorState.activeTool === "pan"
                  ? "cursor-grab"
                  : editor.editorState.activeTool === "move"
                    ? "cursor-default"
                    : "cursor-default"
                : "cursor-grab"
            }`}
          />

          <Show when={ctx.nadData.loading}>
            <div class="absolute inset-0 bg-overlay backdrop-blur-sm grid place-content-center z-20 text-text-on-accent tracking-widest font-bold">
              CHARGEMENT DE LA ZONE...
            </div>
          </Show>

          <NadTooltip />

          <Show when={editor.editorState.isEditing}>
            <div class="absolute top-2 left-1/2 -translate-x-1/2 z-30 pointer-events-none">
              <div
                class="flex items-center gap-2 px-3 py-1 bg-[var(--editor-toolbar-bg)] border border-[var(--editor-accent)] rounded-full text-[10px] font-mono font-bold text-[var(--editor-accent)] shadow-lg"
                style={{ "box-shadow": "0 0 12px var(--editor-accent-glow)" }}
              >
                <span class="w-1.5 h-1.5 rounded-full bg-[var(--editor-accent)] editor-mode-dot" />
                MODE ÉDITION
              </div>
            </div>
          </Show>
        </div>

        <Show when={editor.editorState.isEditing}>
          <EditorInspector />
        </Show>
      </div>

      <Show when={editor.editorState.isEditing}>
        <EditorStatusBar />
      </Show>
    </div>
  );
};
