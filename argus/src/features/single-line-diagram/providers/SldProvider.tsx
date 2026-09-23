/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createContext,
  useContext,
  createSignal,
  createEffect,
  onCleanup,
  type Component,
  type JSX,
} from "solid-js";
import * as d3 from "d3";
import { useSld } from "../hooks/useSld";
import type { SldDiagramParams } from "../types/SldDiagram";

interface SavedViewState {
  x: number;
  y: number;
  k: number;
}

interface SldContextValue {
  viewId: string;
  label: string;
  sldData: () => any;
  svgRef: () => SVGSVGElement | undefined;
  setSvgRef: (el: SVGSVGElement) => void;
  setGRef: (el: SVGGElement) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;
  showProtectionLabels: () => boolean;
  setShowProtectionLabels: (value: boolean) => void;
  showMeasurementLabels: () => boolean;
  setShowMeasurementLabels: (value: boolean) => void;
}

const SldContext = createContext<SldContextValue>();

export const useSldContext = () => {
  const context = useContext(SldContext);
  if (!context) {
    throw new Error("useSldContext must be use in SldProvider");
  }
  return context;
};

interface SldProviderProps {
  viewId: string;
  label: string;
  params: SldDiagramParams;
  children: JSX.Element;
}

export const SldProvider: Component<SldProviderProps> = (props) => {
  const { sld } = useSld(() => props.params);

  const [svgRef, setSvgRef] = createSignal<SVGSVGElement>();
  const [gRef, setGRef] = createSignal<SVGGElement>();

  const [showProtectionLabels, setShowProtectionLabels] = createSignal(true);
  const [showMeasurementLabels, setShowMeasurementLabels] = createSignal(true);

  let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown>;
  let currentViewId: string | null = null;

  const getStorageKey = (id: string) => `sld_d3_view_${id}`;
  const getSavedViewState = (id: string): SavedViewState | null => {
    const raw = localStorage.getItem(getStorageKey(id));
    return raw ? JSON.parse(raw) : null;
  };

  createEffect(() => {
    const svg = svgRef();
    const g = gRef();
    if (!svg || !g) return;

    zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on("zoom", (event) => {
        d3.select(g).attr("transform", event.transform);
      })
      .on("end", (event) => {
        if (!props.viewId) return;
        const state: SavedViewState = {
          x: event.transform.x,
          y: event.transform.y,
          k: event.transform.k,
        };
        localStorage.setItem(
          getStorageKey(props.viewId),
          JSON.stringify(state),
        );
      });

    d3.select(svg).call(zoomBehavior);

    onCleanup(() => {
      d3.select(svg).on(".zoom", null);
    });
  });

  createEffect(() => {
    const svg = svgRef();
    const g = gRef();
    const data = sld();

    if (!data || !svg || !g) return;

    const svgString = data.sld.svg_content || (data.sld as any).svg;
    if (!svgString) return;

    const isNewView = currentViewId !== props.viewId;
    currentViewId = props.viewId;

    const parser = new DOMParser();
    const doc = parser.parseFromString(svgString, "image/svg+xml");
    const incomingSvg = doc.documentElement as unknown as SVGSVGElement;

    const viewBoxAttr = incomingSvg.getAttribute("viewBox");
    if (viewBoxAttr) {
      d3.select(svg).attr("viewBox", viewBoxAttr);
    }

    g.replaceChildren(...Array.from(incomingSvg.childNodes));

    if (isNewView) {
      const savedState = getSavedViewState(props.viewId);
      if (savedState) {
        const t = d3.zoomIdentity
          .translate(savedState.x, savedState.y)
          .scale(savedState.k);
        d3.select(svg).call(zoomBehavior.transform, t);
      } else {
        d3.select(svg).call(zoomBehavior.transform, d3.zoomIdentity);
      }
    }
  });

  // 3. Méthodes de contrôles
  const zoomIn = () => {
    const svg = svgRef();
    if (svg && zoomBehavior)
      d3.select(svg).transition().duration(300).call(zoomBehavior.scaleBy, 1.3);
  };

  const zoomOut = () => {
    const svg = svgRef();
    if (svg && zoomBehavior)
      d3.select(svg).transition().duration(300).call(zoomBehavior.scaleBy, 0.7);
  };

  const resetZoom = () => {
    const svg = svgRef();
    if (svg && zoomBehavior)
      d3.select(svg)
        .transition()
        .duration(300)
        .call(zoomBehavior.transform, d3.zoomIdentity);
  };

  return (
    <SldContext.Provider
      value={{
        viewId: props.viewId,
        label: props.label,
        sldData: sld,
        svgRef,
        setSvgRef,
        setGRef,
        zoomIn,
        zoomOut,
        resetZoom,
        showProtectionLabels,
        setShowProtectionLabels,
        showMeasurementLabels,
        setShowMeasurementLabels,
      }}
    >
      {props.children}
    </SldContext.Provider>
  );
};
