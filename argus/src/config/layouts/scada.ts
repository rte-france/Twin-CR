/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { PanelManifest } from "@/types";

export const leftSidebarPanels: PanelManifest[] = [
  {
    id: "substation",
    label: "Substation",
    iconId: "lucide:folder",
    elementTag: "substation-explorer",
  },
  {
    id: "herge",
    label: "Herge",
    iconId: "ph:map-trifold",
    elementTag: "herge-explorer",
  },
];

export const leftSidebarTools: PanelManifest[] = [];

export const rightSidebarPanels: PanelManifest[] = [
  {
    id: "chart",
    label: "Chart",
    iconId: "lucide:line-chart",
    elementTag: "chart-explorer",
  },
  {
    id: "area",
    label: "Area Network",
    iconId: "flowbite:share-nodes-outline",
    elementTag: "nad-explorer",
  },
  {
    id: "sld",
    label: "Single Line Diagram",
    iconId: "lucide:git-fork",
    elementTag: "sld-explorer",
  },
  {
    id: "ifl",
    label: "Information flow model",
    iconId: "mdi:graph-outline",
    elementTag: "ifl-explorer",
  },
  {
    id: "notifications",
    label: "Notifications",
    iconId: "lucide:bell",
    elementTag: "notifications-panel",
    position: "top",
  },
  {
    id: "network-properties",
    label: "Network properties",
    iconId: "lucide:table",
    elementTag: "network-properties-explorer",
  },
];

export const rightSidebarTools: PanelManifest[] = [
  {
    id: "scada-commands",
    label: "Scada Commands",
    iconId: "mdi:account-school",
    elementTag: "scada-commands",
  },
];
