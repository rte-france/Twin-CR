/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { ManagedRuntime, Layer } from "effect";
import { AppLayer } from "@/config/runtime";

const initRuntime = () => ManagedRuntime.make(AppLayer);

export type AppRuntime = ReturnType<typeof initRuntime>;

// Host singleton for mounting layers
let runtimeInstance: ReturnType<typeof initRuntime> | null = null;

export const getSystemRuntime = () => {
  if (!runtimeInstance) {
    runtimeInstance = initRuntime();
  }
  return runtimeInstance;
};

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
