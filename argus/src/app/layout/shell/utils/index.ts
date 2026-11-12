/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { getSystemRuntime } from "@/utils/getSystemRuntime";

import { Effect } from "effect";
import { WindowBootstrapper } from "@/services/window-bootstrap";

import { DetachPanelOptions, PanelState } from "../types";

export function buildPanelRoute(options: DetachPanelOptions): string {
  const query = new URLSearchParams({
    detached: "true",
    viewType: options.viewType,
    title: options.title,
  });

  if (options.panelLocation) {
    query.set("panelLocation", options.panelLocation);
  }
  if (options.groupId) {
    query.set("groupId", options.groupId);
  }
  if (options.entryUrl) {
    query.set("entryUrl", options.entryUrl);
  }
  if (options.isLocalFile !== undefined) {
    query.set("isLocalFile", String(options.isLocalFile));
  }
  if (options.props && Object.keys(options.props).length > 0) {
    query.set("props", JSON.stringify(options.props));
  }

  return `/panels/${encodeURIComponent(options.id)}?${query.toString()}`;
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
  localStorage.setItem(
    `detached_payload_${id}`,
    JSON.stringify(payloadToStore),
  );

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
