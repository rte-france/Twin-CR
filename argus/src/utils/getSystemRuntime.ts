/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Layer, ManagedRuntime } from "effect";
import { systemRuntime } from "@/config/runtime";

export type AppRuntime = typeof systemRuntime;

export const getSystemRuntime = () => systemRuntime;

declare global {
  interface Window {
    __EFFECT_RUNTIME__?: <A, E, R>(
      layer?: Layer.Layer<A, E, R>,
    ) => Promise<AppRuntime>;
  }
}

export const createRuntime = async <A, E, R>(
  mfeLayer: Layer.Layer<A, E, R> = Layer.empty as any,
): Promise<AppRuntime> => {
  const host = getSystemRuntime();
  const hostContext = (await host.runtime()).context;
  const hostLayer = Layer.succeedContext(hostContext);

  const resolvedMfeLayer = Layer.provide(mfeLayer, hostLayer);
  const composedLayer = Layer.merge(hostLayer, resolvedMfeLayer);

  return ManagedRuntime.make(composedLayer as any) as AppRuntime;
};

window.__EFFECT_RUNTIME__ = createRuntime;
