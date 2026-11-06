/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { Accessor } from "solid-js";

export interface Extent {
  xmin: number;
  ymin: number;
  xmax: number;
  ymax: number;
}

export interface ServiceConfig {
  id: string;
  label: string;
  color: string;
}

export interface LegendItem {
  label: string;
  url: string;
  imageData?: string;
  contentType?: string;
  height: number;
  width: number;
}

export interface LegendLayer {
  layerId: number;
  layerName: string;
  legend: LegendItem[];
}

export interface ArcgisResponse {
  data: string;
  is_image: boolean;
  status: number;
}

export interface HergeContextState {
  extent: Accessor<Extent>;
  setExtent: (e: Extent) => void;
  visibility: Accessor<Record<string, boolean>>;
  toggleService: (id: string) => void;
  activeService: Accessor<string>;
  setActiveService: (id: string) => void;
  loading: Accessor<boolean>;
  setLoading: (v: boolean) => void;
  selectedSchema: Accessor<string | null>;
  setSelectedSchema: (s: string | null) => void;
  schemaFilter: Accessor<string | undefined>;
  services: ServiceConfig[];
  schemasList: Accessor<readonly string[]>;
  legendData: Accessor<readonly any[]>;
  legendLoading: Accessor<boolean>;
  legendError: Accessor<string | null>;
}
