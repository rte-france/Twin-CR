/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createEffect,
  onCleanup,
  on,
  type Accessor,
} from "solid-js";
import { Effect, Fiber, Exit } from "effect";
import L from "leaflet";

import { systemRuntime } from "@/config/runtime";

import { ArcGisService } from "../services/arcgis";
import type { Extent, ServiceConfig } from "../types";
import { REFRESH_DEBOUNCE_MS } from "../config";

import {
  extToLatLngBounds,
  mapToExtent,
  computeScaleBar,
  MAX_RANGE,
  MIN_RANGE,
} from "../utils/leaflet-helpers";

export function useMapOverlays(
  mapAccessor: Accessor<L.Map | null>,
  services: Accessor<ServiceConfig[]>,
  visibility: Accessor<Record<string, boolean>>,
  schemaFilter: Accessor<string | undefined>,
  setLoading: (v: boolean) => void,
) {
  const [scaleInfo, setScaleInfo] = createSignal({ label: "…", widthPx: 80 });
  const [scaleRatio, setScaleRatio] = createSignal(0);

  let refreshFiber: Fiber.Fiber<void, never> | null = null;
  const overlays: Record<string, L.ImageOverlay> = {};

  const scheduleRefresh = (ext?: Extent) => {
    const map = mapAccessor();
    if (!map) return;

    if (refreshFiber) systemRuntime.runFork(Fiber.interrupt(refreshFiber));

    const currentExt = ext ?? mapToExtent(map);
    const rangeX = currentExt.xmax - currentExt.xmin;
    if (rangeX > MAX_RANGE || rangeX < MIN_RANGE) return;

    const size = map.getSize();
    const width = Math.max(size.x, 1);
    const height = Math.max(size.y, 1);

    const sc = computeScaleBar(currentExt, width);
    setScaleInfo({ label: sc.label, widthPx: sc.widthPx });
    setScaleRatio(sc.ratio);

    const currentServices = services();
    const currentVis = visibility();
    const visible = currentServices.filter((s) => currentVis[s.id]);

    // Clean hiding layers
    currentServices.forEach((s) => {
      if (!currentVis[s.id] && overlays[s.id]) {
        overlays[s.id].remove();
        delete overlays[s.id];
      }
    });

    if (visible.length === 0) {
      setLoading(false);
      return;
    }

    const program = Effect.gen(function* () {
      yield* Effect.sleep(REFRESH_DEBOUNCE_MS);
      yield* Effect.sync(() => setLoading(true));

      const arcgis = yield* ArcGisService;
      const bounds = extToLatLngBounds(currentExt);

      const tasks = visible.map((svc) =>
        Effect.gen(function* () {
          const url = yield* arcgis.fetchMapImage(
            svc.id,
            currentExt,
            width,
            height,
            schemaFilter(),
          );

          yield* Effect.sync(() => {
            const idx = currentServices.findIndex((s) => s.id === svc.id);
            const oldOverlay = overlays[svc.id];

            const newOverlay = L.imageOverlay(url, bounds, {
              opacity: 1,
              interactive: false,
              crossOrigin: false,
            });
            newOverlay.setZIndex(idx + 1);

            if (oldOverlay) {
              newOverlay.on(
                "load",
                () => map.hasLayer(oldOverlay) && oldOverlay.remove(),
              );
            }

            newOverlay.addTo(map);
            overlays[svc.id] = newOverlay;
          });
        }).pipe(
          Effect.catchAll((err) => {
            console.error(`Network error ArcGIS for ${svc.id}`, err);
            return Effect.void;
          }),
        ),
      );

      yield* Effect.all(tasks, { concurrency: "unbounded", discard: true });
    }).pipe(
      Effect.onExit((exit) =>
        Effect.sync(() => {
          if (Exit.isSuccess(exit) || Exit.isFailure(exit)) setLoading(false);
        }),
      ),
    );

    refreshFiber = systemRuntime.runFork(program);
  };

  createEffect(
    on(
      () => [visibility(), schemaFilter()],
      () => {
        if (mapAccessor()) scheduleRefresh();
      },
      { defer: true },
    ),
  );

  onCleanup(() => {
    if (refreshFiber) systemRuntime.runFork(Fiber.interrupt(refreshFiber));
    Object.values(overlays).forEach((o) => o.remove());
  });

  return { scheduleRefresh, scaleInfo, scaleRatio };
}
