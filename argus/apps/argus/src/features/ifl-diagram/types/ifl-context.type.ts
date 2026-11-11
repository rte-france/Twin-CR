/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createContext, Resource, Accessor, Setter } from "solid-js";
import { SetStoreFunction } from "solid-js/store";
import { IflResponse, PickInfo } from ".";

export interface IflContextType {
  nodeIds: Accessor<string[]>;
  setNodeIds: Setter<string[]>;
  nodeInput: Accessor<string>;
  setNodeInput: Setter<string>;
  depth: Accessor<number>;
  setDepth: Setter<number>;
  searchQuery: Accessor<string>;
  setSearchQuery: Setter<string>;
  selected: Accessor<PickInfo | null>;
  setSelected: Setter<PickInfo | null>;

  layers: { labels: boolean; };
  setLayers: SetStoreFunction<{
    labels: boolean;
  }>;
  fitEngine?: (xEx: [number, number], yEx: [number, number], cw: number, ch: number) => void

  iflData: Resource<IflResponse>;
  status: Accessor<"idle" | "loading" | "success" | "error">;
  errorMessage: Accessor<string | null>;
  fitCanvas: Accessor<() => void>;
  setFitCanvas: Setter<() => void>;
  triggerLoad: () => void;
  resetView: () => void;
}

export const IflContext = createContext<IflContextType>();
