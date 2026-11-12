/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface DetachPanelOptions {
  id: string;
  title: string;
  viewType: string;
  entryUrl?: string;
  isLocalFile?: boolean;
  props?: Record<string, any>;
  groupId?: string;
  panelLocation?: "central" | "bottom-left" | "bottom-right";
}

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
