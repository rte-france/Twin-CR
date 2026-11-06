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
    id: "dsl",
    label: "Dsl",
    iconId: "lucide:file-terminal",
    elementTag: "dsl-explorer",
  },
  {
    id: "herge",
    label: "Herge",
    iconId: "ph:map-trifold",
    elementTag: "herge-explorer",
    position: "bottom",
  },
];

export const leftSidebarTools: PanelManifest[] = [
  {
    id: "dsl-terminal",
    label: "Dsl Terminal",
    iconId: "lucide:square-terminal",
    elementTag: "dsl-terminal",
  },
  {
    id: "dsl-timeline",
    label: "Dsl Timeline",
    iconId: "ph:equalizer",
    elementTag: "dsl-timeline",
  },
];

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
    id: "ifl",
    label: "Information flow model",
    iconId: "mdi:graph-outline",
    elementTag: "ifl-explorer",
    position: "bottom",
  },
  {
    id: "vnc",
    label: "OMNeT++ View",
    iconId: "lucide:network",
    elementTag: "vnc-explorer",
    position: "bottom",
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
    id: "dynawo-timeline",
    label: "Dynawo Timeline",
    iconId: "mdi:receipt-text-clock-outline",
    elementTag: "dynawo-timeline",
  },
  {
    id: "dynawo-constrains",
    label: "Dynawo Constraints",
    iconId: "mdi:warning-decagram-outline",
    elementTag: "dynawo-constraints",
  },
  {
    id: "gm-commands",
    label: "GM Commands",
    iconId: "mdi:account-tie-hat",
    elementTag: "gm-commands",
  },
  {
    id: "scada-commands",
    label: "Scada Commands",
    iconId: "mdi:account-school",
    elementTag: "scada-commands",
  },
];
