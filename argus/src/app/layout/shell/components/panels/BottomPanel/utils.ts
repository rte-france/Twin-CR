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
import { buildPanelRoute } from "../../dockview/panelUrlBuilder";

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

export const detachPanel = (
  panel: PanelState,
  closeFn: () => void,
  location: "bottom-left" | "bottom-right" = "bottom-left",
) => {
  const { manifest, params } = panel;
  const id = manifest.id;
  const viewType = manifest.elementTag || id;
  const title = manifest.label || "Detached view";

  const payloadToStore = {
    ...manifest,
    elementTag: viewType,
    params,
  };
  localStorage.setItem(`detached_payload_${id}`, JSON.stringify(payloadToStore));

  const targetRoute = buildPanelRoute({
    id,
    title,
    viewType,
    entryUrl: manifest.entryUrl,
    isLocalFile: manifest.isLocalFile,
    props: params,
    panelLocation: location,
  });

  const program = Effect.gen(function* () {
    const wm = yield* WindowBootstrapper;
    yield* wm.createChildFromCurrent(title, targetRoute);
  });

  getSystemRuntime()
    .runPromise(program)
    .then(() => closeFn())
    .catch(console.error);
};
