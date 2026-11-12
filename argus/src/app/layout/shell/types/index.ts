/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { PanelManifest } from "@/types";

export interface DetachPanelOptions {
  id: string;
  title: string;
  viewType: string;
  entryUrl?: string;
  isLocalFile?: boolean;
  props?: Record<string, any>;
  groupId?: string;
  panelLocation?: "central" | "bottom-left" | "bottom-right";
}

export interface PanelState {
  manifest: PanelManifest;
  params: any;
}
