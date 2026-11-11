/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export type PanelId = "left-panel" | "right-panel" | "bottom-panel";

export interface ShellContextType {
  isOpen: (id: PanelId) => boolean;
  dim: (id: PanelId) => number;
  toggle: (id: PanelId) => void;
  setDim: (id: PanelId, value: number) => void;
}

export interface PanelManifest {
  id: string;
  label: string;
  iconId: `${string}:${string}`;
  elementTag: string;
  entryUrl?: string;
  isLocalFile?: boolean;
  position?: "top" | "bottom";
}
