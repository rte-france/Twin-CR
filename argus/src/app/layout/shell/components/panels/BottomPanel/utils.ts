/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { PanelManifest } from "@/types";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { Effect } from "effect";
import { WindowBootstrapper } from "@/services/window-bootstrap";

export interface PanelState {
  manifest: PanelManifest;
  params: any;
}

export const [isLeftOpen, setIsLeftOpen] = createSignal(false);
export const [isRightOpen, setIsRightOpen] = createSignal(false);

export const [activeBottomLeftId, setActiveBottomLeftId] = createSignal<
  string | null
>(null);
export const [activeBottomRightId, setActiveBottomRightId] = createSignal<
  string | null
>(null);

export const hasVisibleBottomPanels = () => isLeftOpen() || isRightOpen();

export const detachPanel = (panel: PanelState, closeFn: () => void) => {
  const { manifest, params } = panel;
  const id = manifest.id;
  const viewType = manifest.elementTag || "default";
  const title = manifest.label || "Detached view";

  if (params) {
    localStorage.setItem(`detached_payload_${id}`, JSON.stringify(params));
  }

  const targetRoute = `/floating/${viewType}/${id}`;

  const program = Effect.gen(function* () {
    const wm = yield* WindowBootstrapper;
    yield* wm.createChildFromCurrent(title, encodeURIComponent(targetRoute));
  });

  getSystemRuntime()
    .runPromise(program)
    .then(() => closeFn())
    .catch(console.error);
};
