/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, ParentComponent } from "solid-js";
import { createStore } from "solid-js/store";
import { PickInfo, IflContext, IflParams } from "../types";
import { useIflData } from "../hooks/useIflData";

export const IflProvider: ParentComponent<IflParams> = (props) => {
  const [nodeIds, setNodeIds] = createSignal<string[]>(props.nodeIds);
  const [depth, setDepth] = createSignal(props.depth);

  const [nodeInput, setNodeInput] = createSignal("");
  const [searchQuery, setSearchQuery] = createSignal("");
  const [selected, setSelected] = createSignal<PickInfo | null>(null);
  const [fitCanvas, setFitCanvas] = createSignal<() => void>(() => () => {});
  const [triggerRefetch, setTriggerRefetch] = createSignal(0);
  const triggerLoad = () => setTriggerRefetch(n => n + 1);

  const [layers, setLayers] = createStore(
    {
      labels: true,
    },
  );

  const [iflData] = useIflData(nodeIds, depth, triggerRefetch);

  const status = () => {
    if (iflData.loading) return "loading";
    if (iflData.error) return "error";
    const data = iflData();
    if (data && !data.success) return "error";
    if (data?.success) return "success";
    return "idle";
  };

  const errorMessage = () => {
    const data = iflData();
    if (data && !data.success) return data.error;
    return null;
  };

  const resetView = () => {
    setSearchQuery("");
    setLayers({labels: true});
    fitCanvas()();
  };

  return (
    <IflContext.Provider
      value={{
        nodeIds,
        setNodeIds,
        nodeInput,
        setNodeInput,
        depth,
        setDepth,
        searchQuery,
        setSearchQuery,
        selected,
        setSelected,
        layers,
        setLayers,
        iflData,
        status,
        errorMessage,
        fitCanvas,
        triggerLoad,
        setFitCanvas,
        resetView,
      }}
    >
      {props.children}
    </IflContext.Provider>
  );
};
