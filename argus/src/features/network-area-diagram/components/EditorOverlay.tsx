/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, For, createMemo, onMount, onCleanup } from "solid-js";
import * as d3 from "d3";
import { useEditorContext } from "../hooks/useEditorContext";
import { useNadContext } from "../hooks/useNadContext";
import { useEditorCommit } from "../hooks/useEditorCommit";

interface EditorOverlayProps {
  transform: () => d3.ZoomTransform;
  containerRef: HTMLElement;
}

// Parse "x1,y1 x2,y2 ..." → [{x,y}, ...]
function parsePoints(pts: string): { x: number; y: number }[] {
  return pts
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((p) => {
      const [x, y] = p.split(",").map(Number);
      return { x, y };
    });
}

// Serialize [{x,y}] → "x1,y1 x2,y2 ..."
function serializePoints(pts: { x: number; y: number }[]): string {
  return pts.map((p) => `${p.x},${p.y}`).join(" ");
}

// Distance squared between two points
function dist2(ax: number, ay: number, bx: number, by: number): number {
  return (ax - bx) ** 2 + (ay - by) ** 2;
}

export const EditorOverlay: Component<EditorOverlayProps> = (props) => {
  const { editorState, selectNode, moveNode, commitMove, setEditorState } =
    useEditorContext();
  const nadCtx = useNadContext();
  const { commitToServer } = useEditorCommit();

  const nodes = createMemo(() => nadCtx.nadData()?.metadata?.nodes ?? []);
  const edges = createMemo(() => nadCtx.nadData()?.metadata?.edges ?? []);

  // Resolve current position for a node (override or original)
  const getNodePos = (svgId: string) => {
    const override = editorState.nodePositions[svgId];
    if (override) return override;
    const node = nodes().find((n) => n.svgId === svgId);
    return node ? { x: node.x, y: node.y } : null;
  };

  // Convert SVG world coords → screen coords
  const toScreen = (x: number, y: number) => {
    const t = props.transform();
    return { sx: t.x + x * t.k, sy: t.y + y * t.k };
  };

  // ── Drag state ────────────────────────────────────────────────────────────
  let dragNodeId: string | null = null;
  let dragStartX = 0;
  let dragStartY = 0;
  let dragOrigX = 0;
  let dragOrigY = 0;

  const handlePointerDown = (
    e: PointerEvent,
    svgId: string,
    origX: number,
    origY: number,
  ) => {
    if (
      editorState.activeTool !== "move" &&
      editorState.activeTool !== "select"
    )
      return;
    e.stopPropagation();
    e.preventDefault();

    selectNode(svgId);
    if (editorState.activeTool !== "move") return;

    const pos = getNodePos(svgId) ?? { x: origX, y: origY };
    dragNodeId = svgId;
    dragOrigX = pos.x;
    dragOrigY = pos.y;

    const t = props.transform();
    dragStartX = (e.clientX - t.x) / t.k;
    dragStartY = (e.clientY - t.y) / t.k;

    setEditorState("isDragging", true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: PointerEvent) => {
    if (!dragNodeId || !editorState.isDragging) return;
    const t = props.transform();
    const cx = (e.clientX - t.x) / t.k;
    const cy = (e.clientY - t.y) / t.k;
    const dx = cx - dragStartX;
    const dy = cy - dragStartY;
    moveNode(dragNodeId, dragOrigX + dx, dragOrigY + dy);
    syncAll(dragNodeId);
  };

  const handlePointerUp = async () => {
    if (!dragNodeId) return;
    commitMove(dragNodeId, dragOrigX, dragOrigY);
    syncAll(dragNodeId);
    dragNodeId = null;
    setEditorState("isDragging", false);
    await commitToServer();
  };

  // ── Master sync: node circle + label + leader + ALL connected edges ───────
  const syncAll = (svgId: string) => {
    const pos = editorState.nodePositions[svgId];
    if (!pos) return;

    const origNode = nodes().find((n) => n.svgId === svgId);
    if (!origNode) return;

    const dx = pos.x - origNode.x;
    const dy = pos.y - origNode.y;

    // 1. Move the VL node <g> (the circle group)
    const nodeGroup = document.getElementById(svgId) as SVGGElement | null;
    if (nodeGroup && nodeGroup.tagName === "g") {
      nodeGroup.setAttribute("transform", `translate(${pos.x},${pos.y})`);
    } else {
      // Sometimes the id is on the circle itself, try parent <g>
      const el = document.getElementById(svgId);
      if (el) {
        const parent = el.closest("g[transform]") as SVGGElement | null;
        if (parent)
          parent.setAttribute("transform", `translate(${pos.x},${pos.y})`);
      }
    }

    // 2. Move the floating text label
    const textNode = document.getElementById(
      `${svgId}-textnode`,
    ) as HTMLElement | null;
    if (textNode) {
      if (!textNode.dataset.origTop) {
        textNode.dataset.origTop = String(parseFloat(textNode.style.top) || 0);
        textNode.dataset.origLeft = String(
          parseFloat(textNode.style.left) || 0,
        );
      }
      textNode.style.top = `${parseFloat(textNode.dataset.origTop!) + dy}px`;
      textNode.style.left = `${parseFloat(textNode.dataset.origLeft!) + dx}px`;
    }

    // 3. Move the leader line (text edge)
    const leaderLine = document.getElementById(
      `${svgId}-textedge`,
    ) as SVGPolylineElement | null;
    if (leaderLine) {
      if (!leaderLine.dataset.origPoints) {
        leaderLine.dataset.origPoints = leaderLine.getAttribute("points") ?? "";
      }
      const orig = parsePoints(leaderLine.dataset.origPoints!);
      const moved = orig.map((p) => ({ x: p.x + dx, y: p.y + dy }));
      leaderLine.setAttribute("points", serializePoints(moved));
    }

    // 4. Update every edge connected to this node
    syncConnectedEdges(svgId, origNode.x, origNode.y, pos.x, pos.y);
  };

  /**
   * For every edge that has svgId as node1 OR node2, find the polyline(s)
   * in the SVG and move the endpoint(s) that were closest to the node's
   * original position.
   *
   * Strategy: for each polyline child of the edge <g>, store original points,
   * then for every point that is within SNAP_RADIUS of the node's original
   * world position, offset it by (newX-origX, newY-origY).
   */
  const syncConnectedEdges = (
    svgId: string,
    origX: number,
    origY: number,
    newX: number,
    newY: number,
  ) => {
    const SNAP_RADIUS_SQ = 60 * 60; // world units²

    const connectedEdges = edges().filter(
      (e) => e.node1 === svgId || e.node2 === svgId,
    );

    for (const edge of connectedEdges) {
      const edgeGroup = document.getElementById(edge.svgId);
      if (!edgeGroup) continue;

      // Collect all polylines and paths inside this edge group
      const pathEls = edgeGroup.querySelectorAll<
        SVGPolylineElement | SVGPathElement
      >("polyline.nad-edge-path, path.nad-edge-path");

      pathEls.forEach((el) => {
        if (el.tagName === "polyline") {
          const poly = el as SVGPolylineElement;

          // Store original points once
          if (!poly.dataset.origPoints) {
            poly.dataset.origPoints = poly.getAttribute("points") ?? "";
          }

          const origPts = parsePoints(poly.dataset.origPoints!);
          const newPts = origPts.map((p) => {
            if (dist2(p.x, p.y, origX, origY) <= SNAP_RADIUS_SQ) {
              return { x: p.x + (newX - origX), y: p.y + (newY - origY) };
            }
            return p;
          });
          poly.setAttribute("points", serializePoints(newPts));
        } else if (el.tagName === "path") {
          // For <path> elements (manhattan/metro layout), we parse the d attribute
          const path = el as SVGPathElement;
          if (!path.dataset.origD) {
            path.dataset.origD = path.getAttribute("d") ?? "";
          }

          const origD = path.dataset.origD!;
          // Replace coordinate pairs that are near origX,origY
          const newD = origD.replace(
            /(-?[\d.]+),(-?[\d.]+)/g,
            (match, px, py) => {
              const x = parseFloat(px);
              const y = parseFloat(py);
              if (dist2(x, y, origX, origY) <= SNAP_RADIUS_SQ) {
                return `${x + (newX - origX)},${y + (newY - origY)}`;
              }
              return match;
            },
          );
          path.setAttribute("d", newD);
        }
      });

      // Also move edge-infos (arrow + label) groups
      // These are positioned relative to edge midpoint — we offset them too
      // if they were near the node
      const infoGroups = edgeGroup.querySelectorAll<SVGGElement>(
        ".nad-edge-infos, .nad-edge-label",
      );
      infoGroups.forEach((g) => {
        const t = g.getAttribute("transform");
        if (!t) return;
        if (!g.dataset.origTransform) {
          g.dataset.origTransform = t;
        }
        const origT = g.dataset.origTransform!;
        // Parse translate(x,y)
        const match = origT.match(/translate\((-?[\d.]+),(-?[\d.]+)\)/);
        if (!match) return;
        const tx = parseFloat(match[1]);
        const ty = parseFloat(match[2]);
        if (dist2(tx, ty, origX, origY) <= SNAP_RADIUS_SQ * 4) {
          // It's close to the node — move it proportionally
          const weight = Math.max(
            0,
            1 - Math.sqrt(dist2(tx, ty, origX, origY)) / (SNAP_RADIUS_SQ * 4),
          );
          g.setAttribute(
            "transform",
            `translate(${tx + (newX - origX) * weight},${ty + (newY - origY) * weight})`,
          );
        }
      });

      // Move transformer winding circles if they sit near the node
      const windings =
        edgeGroup.querySelectorAll<SVGCircleElement>("circle.nad-winding");
      windings.forEach((c) => {
        if (!c.dataset.origCx) {
          c.dataset.origCx = c.getAttribute("cx") ?? "0";
          c.dataset.origCy = c.getAttribute("cy") ?? "0";
        }
        const cx = parseFloat(c.dataset.origCx!);
        const cy = parseFloat(c.dataset.origCy!);
        if (dist2(cx, cy, origX, origY) <= SNAP_RADIUS_SQ) {
          c.setAttribute("cx", String(cx + (newX - origX)));
          c.setAttribute("cy", String(cy + (newY - origY)));
        }
      });
    }
  };

  onMount(() => {
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
  });

  onCleanup(() => {
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", handlePointerUp);
  });

  // Keyboard shortcuts
  onMount(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (!editorState.isEditing) return;
      if (e.key === "s" || e.key === "S") useEditorContext().setTool("select");
      if (e.key === "g" || e.key === "G") useEditorContext().setTool("move");
      if (e.key === "p" || e.key === "P") useEditorContext().setTool("pan");
      if (e.ctrlKey && e.key === "z") {
        e.preventDefault();
        useEditorContext().undo();
      }
      if (e.ctrlKey && e.key === "y") {
        e.preventDefault();
        useEditorContext().redo();
      }
      if (e.key === "Escape") useEditorContext().toggleEditing();
      if (e.key === "Delete" || e.key === "Backspace") {
        // Could implement node deletion here
      }
    };
    window.addEventListener("keydown", handleKey);
    onCleanup(() => window.removeEventListener("keydown", handleKey));
  });

  const getCursor = () => {
    if (editorState.isDragging) return "grabbing";
    if (editorState.activeTool === "move") return "grab";
    if (editorState.activeTool === "select") return "default";
    return "crosshair";
  };

  return (
    <div class="absolute inset-0 pointer-events-none" style={{ "z-index": 15 }}>
      <svg
        class="absolute inset-0 w-full h-full overflow-visible pointer-events-none"
        style={{ "z-index": 16 }}
      >
        {/* Grid overlay */}
        {editorState.showGrid && (
          <EditorGrid
            transform={props.transform}
            containerRef={props.containerRef}
          />
        )}

        {/* Edge highlight lines (selection indicator) */}
        <For each={nodes()}>
          {(node) => {
            const pos = createMemo(() => {
              const p = getNodePos(node.svgId) ?? { x: node.x, y: node.y };
              return toScreen(p.x, p.y);
            });
            const isSelected = () => editorState.selectedNodeId === node.svgId;
            const isHovered = () => editorState.hoveredNodeId === node.svgId;

            return (
              <g>
                {/* Selection ring */}
                {(isSelected() || isHovered()) && (
                  <circle
                    cx={pos().sx}
                    cy={pos().sy}
                    r={isSelected() ? 22 : 18}
                    fill="none"
                    stroke={
                      isSelected()
                        ? "var(--editor-accent)"
                        : "var(--editor-accent-dim)"
                    }
                    stroke-width={isSelected() ? 2 : 1}
                    stroke-dasharray={isSelected() ? "none" : "4 3"}
                    opacity={isSelected() ? 1 : 0.6}
                    class="pointer-events-none"
                    style={{
                      filter: isSelected()
                        ? "drop-shadow(0 0 4px var(--editor-accent-glow))"
                        : "none",
                    }}
                  />
                )}
                {/* Cross hair on selected */}
                {isSelected() && (
                  <>
                    <line
                      x1={pos().sx - 28}
                      y1={pos().sy}
                      x2={pos().sx + 28}
                      y2={pos().sy}
                      stroke="var(--editor-accent)"
                      stroke-width="0.5"
                      opacity="0.4"
                      class="pointer-events-none"
                    />
                    <line
                      x1={pos().sx}
                      y1={pos().sy - 28}
                      x2={pos().sx}
                      y2={pos().sy + 28}
                      stroke="var(--editor-accent)"
                      stroke-width="0.5"
                      opacity="0.4"
                      class="pointer-events-none"
                    />
                  </>
                )}
              </g>
            );
          }}
        </For>
      </svg>

      {/* Hit targets (DOM elements for pointer events) */}
      <div
        class="absolute inset-0 overflow-hidden"
        style={{ "pointer-events": "none", "z-index": 17 }}
      >
        <For each={nodes()}>
          {(node) => {
            const pos = createMemo(() => {
              const p = getNodePos(node.svgId) ?? { x: node.x, y: node.y };
              return toScreen(p.x, p.y);
            });
            const isSelected = () => editorState.selectedNodeId === node.svgId;
            const isMoveTool = () => editorState.activeTool === "move";
            const isSelectTool = () => editorState.activeTool === "select";
            const shouldCapture = () => isMoveTool() || isSelectTool();

            return (
              <div
                style={{
                  position: "absolute",
                  left: `${pos().sx - 20}px`,
                  top: `${pos().sy - 20}px`,
                  width: "40px",
                  height: "40px",
                  "pointer-events": shouldCapture() ? "all" : "none",
                  cursor: isMoveTool()
                    ? editorState.isDragging && isSelected()
                      ? "grabbing"
                      : "grab"
                    : "pointer",
                  "border-radius": "50%",
                }}
                onPointerDown={(e) =>
                  handlePointerDown(e, node.svgId, node.x, node.y)
                }
                onPointerEnter={() =>
                  setEditorState("hoveredNodeId", node.svgId)
                }
                onPointerLeave={() => setEditorState("hoveredNodeId", null)}
              />
            );
          }}
        </For>
      </div>
    </div>
  );
};

/* ── Grid ── */
const EditorGrid: Component<{
  transform: () => d3.ZoomTransform;
  containerRef: HTMLElement;
}> = (props) => {
  const gridSize = 50; // world units

  const gridLines = createMemo(() => {
    const t = props.transform();
    const cw = props.containerRef?.clientWidth ?? 800;
    const ch = props.containerRef?.clientHeight ?? 600;
    const margin = gridSize * 2;

    const worldLeft = (-t.x - margin) / t.k;
    const worldRight = (cw - t.x + margin) / t.k;
    const worldTop = (-t.y - margin) / t.k;
    const worldBottom = (ch - t.y + margin) / t.k;

    const startX = Math.floor(worldLeft / gridSize) * gridSize;
    const startY = Math.floor(worldTop / gridSize) * gridSize;

    const lines: {
      x1: number;
      y1: number;
      x2: number;
      y2: number;
      isMain: boolean;
    }[] = [];

    for (let x = startX; x <= worldRight; x += gridSize) {
      const sx = t.x + x * t.k;
      lines.push({
        x1: sx,
        y1: 0,
        x2: sx,
        y2: ch,
        isMain: Math.abs(x % (gridSize * 5)) < 0.01,
      });
    }
    for (let y = startY; y <= worldBottom; y += gridSize) {
      const sy = t.y + y * t.k;
      lines.push({
        x1: 0,
        y1: sy,
        x2: cw,
        y2: sy,
        isMain: Math.abs(y % (gridSize * 5)) < 0.01,
      });
    }

    return lines;
  });

  return (
    <g class="editor-grid">
      <For each={gridLines()}>
        {(line) => (
          <line
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke={
              line.isMain
                ? "var(--editor-grid-main)"
                : "var(--editor-grid-minor)"
            }
            stroke-width={line.isMain ? 0.8 : 0.4}
            class="pointer-events-none"
          />
        )}
      </For>
    </g>
  );
};
