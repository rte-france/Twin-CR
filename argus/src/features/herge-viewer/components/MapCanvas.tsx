/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  type Component,
  createSignal,
  onMount,
  onCleanup,
  createEffect,
} from "solid-js";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { useHerge } from "../hooks/useHerge";
import { SCHEMATIC_EXTENT, ZOOM_IN_FACTOR, ZOOM_OUT_FACTOR } from "../config";
import {
  extToLatLngBounds,
  mapToExtent,
  MAX_RANGE,
  MIN_RANGE,
} from "../utils/leaflet-helpers";
import { useMapIdentify } from "../hooks/useMapIdentify";
import { useMapOverlays } from "../hooks/useMapOverlays";

import {
  MapLoadingOverlay,
  MapEmptyState,
  MapScaleBar,
  MapCoordsBar,
} from "./MapUI";
import { MapPopup } from "./MapPopup";
import { MapGrid } from "./MapGrid";
import { MapTools } from "./MapTools";

export const MapCanvas: Component = () => {
  const ctx = useHerge();
  let mapContainer!: HTMLDivElement;
  let mapInstance: L.Map;

  const [map, setMap] = createSignal<L.Map | null>(null);
  const [mouseCoords, setMouseCoords] = createSignal({ x: 0, y: 0 });

  const { popupData, popupPos, clearPopup, runIdentify } = useMapIdentify();
  const { scheduleRefresh, scaleInfo, scaleRatio } = useMapOverlays(
    map,
    () => ctx.services,
    ctx.visibility,
    ctx.schemaFilter,
    ctx.setLoading,
  );

  onMount(() => {
    const initExt = ctx.extent();
    mapInstance = L.map(mapContainer, {
      crs: L.CRS.Simple,
      zoomControl: false,
      attributionControl: false,
      preferCanvas: true,
      minZoom: -15,
      maxZoom: 10,
      zoomSnap: 0.1,
      wheelPxPerZoomLevel: 120,
    });

    mapInstance.fitBounds(extToLatLngBounds(initExt));

    mapInstance.on("moveend zoomend", () => {
      const ext = mapToExtent(mapInstance);
      ctx.setExtent(ext);
      scheduleRefresh(ext);
    });

    mapInstance.on("mousemove", (e: L.LeafletMouseEvent) => {
      setMouseCoords({
        x: Math.round(e.latlng.lng),
        y: Math.round(e.latlng.lat),
      });
    });

    mapInstance.on("movestart", clearPopup);

    mapInstance.on("click", (e: L.LeafletMouseEvent) => {
      const visibleServices = ctx.services.filter(
        (s) => ctx.visibility()[s.id],
      );
      runIdentify(mapInstance, e, mapToExtent(mapInstance), visibleServices);
    });

    let resizeTimeout: ReturnType<typeof setTimeout>;
    let initTimeout: ReturnType<typeof setTimeout>;
    const resizeObserver = new ResizeObserver((entries) => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        const currentMap = map();

        if (currentMap && mapContainer && mapContainer.isConnected) {
          const { width, height } = entries[0].contentRect;

          if (width > 0 && height > 0) {
            currentMap.invalidateSize(false);

            const newExt = mapToExtent(currentMap);
            ctx.setExtent(newExt);
            scheduleRefresh(newExt);
          }
        }
      }, 100);
    });

    resizeObserver.observe(mapContainer);
    setMap(mapInstance);

    initTimeout = setTimeout(() => {
      const currentMap = map();
      if (currentMap) {
        currentMap.invalidateSize();
        scheduleRefresh(initExt);
      }
    }, 50);

    onCleanup(() => {
      clearTimeout(resizeTimeout);
      clearTimeout(initTimeout);
      resizeObserver.disconnect();

      if (mapInstance) {
        mapInstance.remove();
      }
      setMap(null);
    });
  });

  createEffect(() => {
    const currentMap = map();
    if (!currentMap) return;
    const bounds = extToLatLngBounds(ctx.extent());
    if (!currentMap.getBounds().pad(0.05).contains(bounds)) {
      currentMap.fitBounds(bounds, {
        padding: [30, 30],
        animate: true,
        duration: 0.8,
      });
    }
  });

  const applyZoom = (factor: number) => {
    const currentMap = map();
    if (!currentMap) return;
    const ext = mapToExtent(currentMap);
    const rangeX = (ext.xmax - ext.xmin) * factor;
    const rangeY = (ext.ymax - ext.ymin) * factor;

    if (factor > 1 && rangeX > MAX_RANGE) return;
    if (factor < 1 && rangeX < MIN_RANGE) return;

    const cx = (ext.xmin + ext.xmax) / 2;
    const cy = (ext.ymin + ext.ymax) / 2;
    currentMap.fitBounds([
      [cy - rangeY / 2, cx - rangeX / 2],
      [cy + rangeY / 2, cx + rangeX / 2],
    ]);
  };

  const goHome = () => {
    const currentMap = map();
    if (!currentMap) return;
    ctx.setExtent({ ...SCHEMATIC_EXTENT });
    currentMap.fitBounds(extToLatLngBounds(SCHEMATIC_EXTENT));
    scheduleRefresh({ ...SCHEMATIC_EXTENT });
  };

  const hasVisibleLayers = () =>
    ctx.services.some((s) => ctx.visibility()[s.id]);

  return (
    <div class="relative flex-1 overflow-hidden map-wrapper group">
      <MapGrid
        ref={(el) => {
          mapContainer = el;
        }}
      />

      <MapLoadingOverlay show={ctx.loading()} />
      <MapEmptyState show={!hasVisibleLayers()} />

      <div class="z-400 pointer-events-none opacity-0 transition-opacity duration-300 group-hover:opacity-100">
        <MapScaleBar widthPx={scaleInfo().widthPx} label={scaleInfo().label} />
        <MapCoordsBar
          x={mouseCoords().x}
          y={mouseCoords().y}
          ratio={scaleRatio()}
        />
      </div>

      <div class="absolute right-3.5 bottom-3.5 z-500 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
        <MapTools
          onGoHome={goHome}
          onZoomIn={() => applyZoom(ZOOM_IN_FACTOR)}
          onZoomOut={() => applyZoom(ZOOM_OUT_FACTOR)}
        />
      </div>

      <MapPopup data={popupData()} pos={popupPos()} onClose={clearPopup} />
    </div>
  );
};
