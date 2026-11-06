/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createContext,
  useContext,
  type JSX,
  type Accessor,
} from "solid-js";

export type PlacementMode = "left" | "right" | "above" | "below" | "within";

interface PlacementContextValue {
  placement: Accessor<PlacementMode>;
  setPlacement: (mode: PlacementMode) => void;
}

const PlacementContext = createContext<PlacementContextValue>();

export function PlacementProvider(props: { children: JSX.Element }) {
  const [placement, setPlacement] = createSignal<PlacementMode>("within");

  return (
    <PlacementContext.Provider value={{ placement, setPlacement }}>
      {props.children}
    </PlacementContext.Provider>
  );
}

export function usePlacement() {
  const context = useContext(PlacementContext);
  if (!context)
    throw new Error("usePlacement must be used within PlacementProvider");
  return context;
}
