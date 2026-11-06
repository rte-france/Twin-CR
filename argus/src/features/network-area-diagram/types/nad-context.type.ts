/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createContext, Resource, Accessor, Setter } from "solid-js";
import { SetStoreFunction } from "solid-js/store";
import { EquipmentLayer, NadResponse, PickInfo } from "../types";

export interface NadContextType {
  vlIds: Accessor<string[]>;
  setVlIds: Setter<string[]>;
  vlInput: Accessor<string>;
  setVlInput: Setter<string>;
  depth: Accessor<number>;
  setDepth: Setter<number>;
  layout: Accessor<"default" | "geographical">;
  setLayout: Setter<"default" | "geographical">;
  radiusFactor: Accessor<number>;
  setRadiusFactor: Setter<number>;
  searchQuery: Accessor<string>;
  setSearchQuery: Setter<string>;
  selected: Accessor<PickInfo | null>;
  setSelected: Setter<PickInfo | null>;

  layers: { labels: boolean; edgeInfos: boolean; injections: boolean };
  setLayers: SetStoreFunction<{
    labels: boolean;
    edgeInfos: boolean;
    injections: boolean;
  }>;
  vlLayers: Record<string, boolean>;
  setVlLayers: SetStoreFunction<Record<string, boolean>>;

  equipmentLayers: EquipmentLayer;
  setEquipmentLayers: SetStoreFunction<EquipmentLayer>;

  flowType: Accessor<"active" | "reactive" | "current">;
  setFlowType: Setter<"active" | "reactive" | "current">;
  hideDisconnected: Accessor<boolean>;
  setHideDisconnected: Setter<boolean>;

  layoutMode: Accessor<"default" | "manhattan" | "octolinear">;
  setLayoutMode: Setter<"default" | "manhattan" | "octolinear">;

  nadData: Resource<NadResponse | undefined>;
  status: Accessor<"idle" | "loading" | "success" | "error">;
  fitCanvas: Accessor<() => void>;
  setFitCanvas: Setter<() => void>;
  triggerLoad: () => void;
  resetView: () => void;

  fixedPositions: Accessor<any[] | null>;
  setFixedPositions: Setter<any[] | null>;
}

export const NadContext = createContext<NadContextType>();
