/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { Extent, ServiceConfig } from "./types";

export const SCHEMATIC_EXTENT: Extent = {
  xmin: -110000,
  ymin: -25000,
  xmax: 110000,
  ymax: 100000,
};

export const MAX_BOUNDS_LAMBERT: [[number, number], [number, number]] = [
  [6_000_000, 100_000],
  [7_200_000, 1_250_000],
];

export const SERVICES: ServiceConfig[] = [
  { id: "SCHEMAS", label: "Schémas", color: "var(--srv-schemas)" },
  { id: "DESSIN_CAD", label: "Dessin CAD", color: "var(--srv-cad)" },
  // {
  //   id: "27_DESSIN_CAD_REPRISE_HERGE_CAD_HERGE405;AUTRE;_ACR;_AMU;_CONDO;_GDP;_GMR;_CONSO;_QDE;_RVU;_SAS;_TDS;_ZAB;_EVENEMENTIEL;_RFD;_RADIALES",
  //   label: "toto",
  //   color: "var(--srv-cad)",
  // },

  { id: "SEARCH", label: "Recherche", color: "var(--srv-search)" },
  { id: "Jeux_De_Barres", label: "Jeux de Barres", color: "var(--srv-barres)" },
  { id: "Liaisons", label: "Liaisons", color: "var(--srv-liaisons)" },
  {
    id: "Transformateur",
    label: "Transformateur",
    color: "var(--srv-transfo)",
  },
  { id: "Automates", label: "Automates", color: "var(--srv-automates)" },
  { id: "Postes", label: "Postes", color: "var(--srv-postes)" },
  {
    id: "Moyens_de_Compensation",
    label: "Moyens de Compensation",
    color: "var(--srv-compensation)",
  },
  { id: "Production", label: "Production", color: "var(--srv-production)" },
  {
    id: "Organes_de_Coupure",
    label: "Organes de Coupure",
    color: "var(--srv-coupure)",
  },
  { id: "SdQ_R7", label: "SdQ R7", color: "var(--srv-sdq)" },
  { id: "ANNOTATIONS", label: "Annotations", color: "var(--srv-annotations)" },
  { id: "SPORT", label: "SPORT", color: "var(--srv-sport)" },
];

export const DEFAULT_DISABLED_LAYERS = ["SdQ_R7", "ANNOTATIONS", "SPORT"];
export const DEFAULT_VISIBILITY = Object.fromEntries(
  SERVICES.map((s) => [s.id, !DEFAULT_DISABLED_LAYERS.includes(s.id)]),
);

export const ZOOM_IN_FACTOR = 0.5;
export const ZOOM_OUT_FACTOR = 2.0;
export const WHEEL_IN_FACTOR = 0.9;
export const WHEEL_OUT_FACTOR = 1.1;
export const REFRESH_DEBOUNCE_MS = "150 millis";
