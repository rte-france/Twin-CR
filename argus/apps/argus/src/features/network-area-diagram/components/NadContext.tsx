/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createResource,
  ParentComponent,
  createEffect,
} from "solid-js";
import { createStore } from "solid-js/store";
import { NadResponse, PickInfo, VL_COLORS, NadContext, Nad } from "../types";
import { backendGet } from "@/services/backend";

export const NadProvider: ParentComponent<Nad> = (props) => {
  const [vlIds, setVlIds] = createSignal<string[]>(props.params.vlIds);
  const [depth, setDepth] = createSignal(props.params.depth);
  const [layout, setLayout] = createSignal(props.params.layout);
  const [radiusFactor, setRadiusFactor] = createSignal(props.params.radiusFactor);
  const [flowType, setFlowType] = createSignal(props.params.flowType);
  const [layoutMode, setLayoutMode] = createSignal(props.params.layoutMode);

  const [vlInput, setVlInput] = createSignal("");
  const [searchQuery, setSearchQuery] = createSignal("");
  const [selected, setSelected] = createSignal<PickInfo | null>(null);
  const [fitCanvas, setFitCanvas] = createSignal<() => void>(() => () => {});
  const [fixedPositions, setFixedPositions] = createSignal<any[] | null>(null);
  const [hideDisconnected, setHideDisconnected] = createSignal(false);

  const [layers, setLayers] = createStore(props.params.layers);

  const [equipmentLayers, setEquipmentLayers] = createStore(props.params.equipmentLayers);

  const [vlLayers, setVlLayers] = createStore(
    Object.keys(VL_COLORS).reduce((acc, key) => ({ ...acc, [key]: true }), {}),
  );

  const [fetchArgs, setFetchArgs] = createSignal<{
    ids: string[];
    d: number;
    positions?: any[] | null;
    layout: string;
    radiusFactor: number;
  } | null>(null);

  const [nadData] = createResource(fetchArgs, async (args) => {
    const primaryId = args.ids[0] || "";
    const params = new URLSearchParams({
      voltageLevels: args.ids.join(","),
      depth: String(args.d),
      layout: args.layout,
      radiusFactor: String(args.radiusFactor),
    });

    if (args.positions && args.positions.length > 0) {
      params.set("fixed_positions", JSON.stringify(args.positions));
    }

    const queryString = params.toString().replace(/\+/g, "%20");
    const endpoint = `/nad/${encodeURIComponent(primaryId)}?${queryString}`;

    const rawData = await backendGet<any>(endpoint).catch(() => {
      throw new Error("Failed to fetch NAD data from server");
    });
    try {
      const svg_content = rawData.svg_content || rawData.svg || "";
      let metadata = rawData.metadata || {};
      if (typeof metadata === "string") metadata = JSON.parse(metadata);
      return { ...rawData, svg_content, metadata } as NadResponse;
    } catch {
      throw new Error("Parsing metadata failed");
    }
  });

  const triggerLoad = () => {
    if (vlIds().length > 0) {
      setFetchArgs({
        ids: vlIds(),
        d: depth(),
        positions: fixedPositions(),
        layout: layout(),
        radiusFactor: radiusFactor(),
      });
    }
  };

  const status = () => {
    if (nadData.loading) return "loading";
    if (nadData.error) return "error";
    if (nadData()) return "success";
    return "idle";
  };

  const resetView = () => {
    setSearchQuery("");
    setFlowType("active");
    setLayoutMode("default");
    fitCanvas()();
  };

  createEffect(() => {
    if (vlIds().length > 0 && status() === "idle") {
      triggerLoad();
    }
  });


  return (
    <NadContext.Provider
      value={{
        vlIds,
        setVlIds,
        vlInput,
        setVlInput,
        depth,
        setDepth,
        layout,
        setLayout,
        radiusFactor,
        setRadiusFactor,
        searchQuery,
        setSearchQuery,
        selected,
        setSelected,
        layers,
        setLayers,
        vlLayers,
        setVlLayers,
        equipmentLayers,
        setEquipmentLayers,
        flowType,
        setFlowType,
        hideDisconnected,
        setHideDisconnected,
        layoutMode,
        setLayoutMode,
        nadData,
        status,
        triggerLoad,
        fitCanvas,
        setFitCanvas,
        resetView,
        fixedPositions,
        setFixedPositions,
      }}
    >
      {props.children}
    </NadContext.Provider>
  );
};
