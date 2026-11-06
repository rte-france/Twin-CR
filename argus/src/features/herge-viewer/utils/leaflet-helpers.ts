/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import L from "leaflet";
import type { Extent } from "../types";

const HIGHLIGHT_STYLE = {
  color: "#00ffff",
  weight: 4,
  opacity: 0.8,
  fillColor: "#00ffff",
  fillOpacity: 0.2,
};
export const MAX_RANGE = 5_000_000;
export const MIN_RANGE = 10;

export const extToLatLngBounds = (ext: Extent): L.LatLngBoundsLiteral => [
  [ext.ymin, ext.xmin], // SW
  [ext.ymax, ext.xmax], // NE
];

export const mapToExtent = (map: L.Map): Extent => {
  const b = map.getBounds();
  return {
    xmin: b.getWest(),
    xmax: b.getEast(),
    ymin: b.getSouth(),
    ymax: b.getNorth(),
  };
};

export const computeScaleBar = (ext: Extent, widthPx: number) => {
  const mpp = (ext.xmax - ext.xmin) / widthPx;
  const ratio = Math.round((mpp * 96) / 0.0254);
  const rawM = 80 * mpp;

  let snapped: number, label: string;

  if (rawM >= 100_000) {
    snapped = Math.round(rawM / 100_000) * 100_000;
    label = `${snapped / 1000} km`;
  } else if (rawM >= 10_000) {
    snapped = Math.round(rawM / 10_000) * 10_000;
    label = `${snapped / 1000} km`;
  } else if (rawM >= 1_000) {
    snapped = Math.round(rawM / 1_000) * 1_000;
    label = `${snapped / 1000} km`;
  } else {
    snapped = Math.round(rawM / 100) * 100 || 100;
    label = `${snapped} m`;
  }

  return { label, widthPx: Math.round(snapped / mpp), ratio };
};

export const createHighlightLayer = (
  geometry: any,
  geomType: string,
): L.Layer | null => {
  if (!geometry) return null;

  switch (geomType) {
    case "esriGeometryPoint":
      return L.circleMarker([geometry.y, geometry.x], {
        ...HIGHLIGHT_STYLE,
        radius: 8,
      });

    case "esriGeometryPolyline":
      const lines = geometry.paths.map((path: number[][]) =>
        path.map((pt) => [pt[1], pt[0]] as [number, number]),
      );
      return L.polyline(lines, HIGHLIGHT_STYLE);

    case "esriGeometryPolygon":
      const polygons = geometry.rings.map((ring: number[][]) =>
        ring.map((pt) => [pt[1], pt[0]] as [number, number]),
      );
      return L.polygon(polygons, HIGHLIGHT_STYLE);

    default:
      return null;
  }
};
