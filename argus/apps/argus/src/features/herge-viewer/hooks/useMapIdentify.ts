/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onCleanup } from "solid-js";
import { Effect, Exit } from "effect";
import L from "leaflet";

import { systemRuntime } from "@/config/runtime";
import { ArcGisService } from "../services/arcgis";
import type { ServiceConfig, Extent } from "../types";
import { createHighlightLayer } from "../utils/leaflet-helpers";

export function useMapIdentify() {
  const [popupData, setPopupData] = createSignal<any | null>(null);
  const [popupPos, setPopupPos] = createSignal({ x: 0, y: 0 });

  let cancelIdentify: (() => void) | null = null;
  let highlightGroup: L.FeatureGroup | null = null;

  const clearPopup = () => {
    setPopupData(null);
    if (highlightGroup) {
      highlightGroup.clearLayers();
    }
  };

  const runIdentify = (
    map: L.Map,
    e: L.LeafletMouseEvent,
    currentExt: Extent,
    visibleServices: ServiceConfig[],
  ) => {
    if (cancelIdentify) cancelIdentify();

    if (!highlightGroup) {
      highlightGroup = L.featureGroup().addTo(map);
    }

    if (visibleServices.length === 0) {
      clearPopup();
      return;
    }

    map.getContainer().style.cursor = "wait";
    const size = map.getSize();
    const clickX = e.latlng.lng;
    const clickY = e.latlng.lat;

    const program = Effect.gen(function* () {
      const arcgis = yield* ArcGisService;

      const tasks = visibleServices.map((svc) =>
        arcgis
          .fetchIdentify(svc.id, clickX, clickY, currentExt, size.x, size.y)
          .pipe(
            Effect.map((results) =>
              results.map((r: any) => ({
                ...r,
                _serviceId: svc.id,
                _serviceLabel: svc.label,
              })),
            ),
            Effect.catchAll((error) => {
              console.error(`Erreur Identify for ${svc.id}:`, error);
              return Effect.succeed([]);
            }),
          ),
      );

      const results = yield* Effect.all(tasks, { concurrency: "unbounded" });
      return results.flat();
    }).pipe(
      Effect.ensuring(
        Effect.sync(() => {
          if (map) map.getContainer().style.cursor = "";
        }),
      ),
    );

    cancelIdentify = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit)) {
          const allResults = exit.value;

          if (allResults.length > 0) {
            const equipements = allResults.filter(
              (r) =>
                r.geometryType !== "esriGeometryPolygon" &&
                !r.layerName.toLowerCase().includes("schéma"),
            );

            const resultToDisplay =
              equipements.length > 0 ? equipements[0] : allResults[0];

            highlightGroup!.clearLayers();
            const layer = createHighlightLayer(
              resultToDisplay.geometry,
              resultToDisplay.geometryType,
            );
            if (layer) {
              highlightGroup!.addLayer(layer);
            }

            const point = map.latLngToContainerPoint(e.latlng);
            setTimeout(() => {
              setPopupPos({ x: point.x, y: point.y });
              setPopupData(resultToDisplay);
            }, 10);
          } else {
            clearPopup();
          }
        } else {
          clearPopup();
        }
        cancelIdentify = null;
      },
    });
  };

  onCleanup(() => {
    if (cancelIdentify) cancelIdentify();
  });

  return { popupData, popupPos, clearPopup, runIdentify };
}
