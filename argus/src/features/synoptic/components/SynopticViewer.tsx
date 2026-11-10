/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, createSignal, For, onCleanup, Show, type Component } from "solid-js";
import { FiMaximize, FiZoomIn, FiZoomOut } from "solid-icons/fi";
import * as d3 from "d3";
import { backendGet } from "@/services/backend";
import type { RenderedSynoptic, SynopticViewerParams } from "../types";
import { equipmentProperties, type EquipmentProperties } from "../equipmentProperties";
import { SldActionPanel } from "@/features/single-line-diagram/components/SldActionPanel";
import type { SelectedActionItem } from "@/features/single-line-diagram/hooks/useActionPanelSelection";

interface Hovered {
  id: string;
  tooltip: string;
  x: number;
  y: number;
  properties?: EquipmentProperties | null;
}

// Element of the rendered SVG showing a network equipment (data-equipment, see SynopticRenderer)
const equipmentElement = (target: EventTarget | null) =>
  target instanceof Element ? target.closest<SVGElement>("[data-equipment]") : null;

const REFRESH_MS = 2000;
const storageKey = (name: string) => `synoptic_d3_view_${name}`;

/**
 * Shows a synoptic rendered by the backend (GET /synoptic/{name}), refreshed periodically.
 * The whole SVG is swapped at each refresh, the zoom/pan state is kept (and saved per synoptic).
 */
export const SynopticViewer: Component<SynopticViewerParams> = (props) => {
  let svgRef: SVGSVGElement | undefined;
  let gRef: SVGGElement | undefined;
  let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | undefined;
  let loadedName: string | null = null;
  const [error, setError] = createSignal<string | null>(null);
  const [lastSync, setLastSync] = createSignal<number | null>(null);
  const [hovered, setHovered] = createSignal<Hovered | null>(null);
  const [selected, setSelected] = createSignal<SelectedActionItem>(null);
  let containerRef: HTMLDivElement | undefined;

  const onMouseMove = (e: MouseEvent) => {
    const el = equipmentElement(e.target);
    if (!el || !containerRef) {
      setHovered(null);
      return;
    }
    const id = el.dataset.equipment!;
    const rect = containerRef.getBoundingClientRect();
    const position = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    const current = hovered();
    if (current?.id === id) {
      setHovered({ ...current, ...position });
      return;
    }
    setHovered({ id, tooltip: el.dataset.tooltip ?? id, ...position });
    equipmentProperties(id).then((properties) => {
      const h = hovered();
      if (h?.id === id) setHovered({ ...h, properties });
    });
  };

  const onContextMenu = (e: MouseEvent) => {
    const el = equipmentElement(e.target);
    if (!el) return;
    e.preventDefault();
    setHovered(null);
    setSelected({ equipmentId: el.dataset.equipment!, side: null });
  };

  // Close the context menu on a click outside of it (as in the single line diagram)
  const onDocumentClick = (e: MouseEvent) => {
    if (selected() && !(e.target instanceof Element && e.target.closest("[data-action-panel]"))) setSelected(null);
  };
  document.addEventListener("click", onDocumentClick);
  onCleanup(() => document.removeEventListener("click", onDocumentClick));

  const fit = () => {
    if (!svgRef || !zoomBehavior) return;
    d3.select(svgRef).transition().duration(300).call(zoomBehavior.transform, d3.zoomIdentity);
  };

  const zoomBy = (k: number) => {
    if (!svgRef || !zoomBehavior) return;
    d3.select(svgRef).transition().duration(200).call(zoomBehavior.scaleBy, k);
  };

  createEffect(() => {
    if (!svgRef || !gRef) return;
    const g = gRef;
    zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 40])
      .on("zoom", (event) => d3.select(g).attr("transform", event.transform))
      .on("end", (event) => {
        if (!props.name) return;
        const { x, y, k } = event.transform;
        try {
          localStorage.setItem(storageKey(props.name), JSON.stringify({ x, y, k }));
        } catch {
          /* storage unavailable */
        }
      });
    d3.select(svgRef).call(zoomBehavior).on("dblclick.zoom", null);
    onCleanup(() => {
      if (svgRef) d3.select(svgRef).on(".zoom", null);
    });
  });

  const apply = (rendered: RenderedSynoptic) => {
    if (!svgRef || !gRef || !zoomBehavior) return;
    const doc = new DOMParser().parseFromString(rendered.svg, "image/svg+xml");
    const incoming = doc.documentElement;
    if (incoming.nodeName !== "svg") return;
    svgRef.setAttribute("viewBox", incoming.getAttribute("viewBox") ?? "0 0 1000 1000");
    for (const attr of ["font-family", "font-size"]) {
      const v = incoming.getAttribute(attr);
      if (v) gRef.setAttribute(attr, v);
    }
    gRef.replaceChildren(...Array.from(incoming.childNodes).map((n) => document.importNode(n, true)));
    // The hover card replaces the native tooltip of the equipments
    gRef.querySelectorAll<SVGElement>("[data-equipment]").forEach((el) => {
      const title = el.querySelector(":scope > title");
      if (title) {
        el.dataset.tooltip = title.textContent ?? "";
        title.remove();
      }
    });

    if (loadedName !== props.name) {
      // First display of this synoptic: restore the saved view, if any
      loadedName = props.name;
      let saved: { x: number; y: number; k: number } | null = null;
      try {
        saved = JSON.parse(localStorage.getItem(storageKey(props.name)) ?? "null");
      } catch {
        saved = null;
      }
      const t = saved ? d3.zoomIdentity.translate(saved.x, saved.y).scale(saved.k) : d3.zoomIdentity;
      d3.select(svgRef).call(zoomBehavior.transform, t);
    }
  };

  createEffect(() => {
    const name = props.name;
    if (!name) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      try {
        const rendered = await backendGet<RenderedSynoptic>(`/synoptic/${encodeURIComponent(name)}`);
        if (cancelled) return;
        apply(rendered);
        setError(null);
        setLastSync(Date.now());
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
      if (!cancelled) timer = setTimeout(tick, REFRESH_MS);
    };
    tick();

    onCleanup(() => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    });
  });

  return (
    <div ref={containerRef} class="relative w-full h-full overflow-hidden bg-[#1c3f41]">
      <svg
        ref={svgRef}
        class="w-full h-full block cursor-grab active:cursor-grabbing [&_[data-equipment]]:cursor-pointer"
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={onMouseMove}
        onMouseLeave={() => setHovered(null)}
        onContextMenu={onContextMenu}
      >
        <g ref={gRef} />
      </svg>

      <div class="absolute top-2 right-2 flex gap-1">
        <button class="p-1.5 rounded bg-bg/80 text-fg hover:text-links" title="Zoom in" onClick={() => zoomBy(1.4)}>
          <FiZoomIn class="size-4" />
        </button>
        <button class="p-1.5 rounded bg-bg/80 text-fg hover:text-links" title="Zoom out" onClick={() => zoomBy(1 / 1.4)}>
          <FiZoomOut class="size-4" />
        </button>
        <button class="p-1.5 rounded bg-bg/80 text-fg hover:text-links" title="Fit" onClick={fit}>
          <FiMaximize class="size-4" />
        </button>
      </div>

      <Show when={hovered() && !selected() && hovered()}>
        {(h) => (
          <div
            class="absolute z-10 pointer-events-none max-w-[320px] px-2 py-1.5 rounded-md text-[11px] bg-[var(--popover-bg)] text-[var(--fg)] border border-[var(--popover-border)] shadow-[var(--popover-shadow)]"
            style={{ left: `${h().x + 14}px`, top: `${h().y + 14}px` }}
          >
            <div class="font-semibold break-all">{h().tooltip}</div>
            <Show when={h().properties}>
              {(p) => (
                <div class="mt-1 grid grid-cols-[auto_1fr] gap-x-2 font-mono text-[10px]">
                  <span class="opacity-60">type</span>
                  <span>{p().type}</span>
                  <For each={p().values}>
                    {([k, v]) => (
                      <>
                        <span class="opacity-60">{k}</span>
                        <span class="break-all">{String(v)}</span>
                      </>
                    )}
                  </For>
                </div>
              )}
            </Show>
          </div>
        )}
      </Show>

      <SldActionPanel SelectedActionItem={selected()} onClose={() => setSelected(null)} />

      <Show when={error()}>
        <div class="absolute bottom-2 left-2 max-w-[60%] px-2 py-1 rounded text-[11px] bg-[var(--warning-bg)] text-[var(--warning-icon)] truncate" title={error() ?? ""}>
          {lastSync() ? "Update failed, showing the last received values: " : "Cannot load the synoptic: "}
          {error()}
        </div>
      </Show>
    </div>
  );
};
