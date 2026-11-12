/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect, beforeEach } from "vitest";
import { hydratePanelFromUrlAndStorage } from "@/app/routes/floating/panelHydration";

describe("Panel Hydration from URL", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("hydrates completely from URL search params without storage", () => {
    const rawId = "viewer-123";
    const searchParams = {
      viewType: "network-viewer",
      title: "Network Viewer",
      entryUrl: "https://example.com/entry.js",
      props: encodeURIComponent(JSON.stringify({ zoom: 1.5, theme: "dark" })),
    };

    const state = hydratePanelFromUrlAndStorage(rawId, searchParams);

    expect(state.id).toBe("viewer-123");
    expect(state.manifest.elementTag).toBe("network-viewer");
    expect(state.manifest.label).toBe("Network Viewer");
    expect(state.manifest.entryUrl).toBe("https://example.com/entry.js");
    expect(state.componentProps).toEqual({ zoom: 1.5, theme: "dark" });
  });

  it("falls back to storage if present for legacy payloads", () => {
    const rawId = "panel-456";
    localStorage.setItem(
      "detached_payload_panel-456",
      JSON.stringify({
        elementTag: "scada-chart",
        label: "Chart View",
        params: { seriesId: "S1" },
      }),
    );

    const state = hydratePanelFromUrlAndStorage(rawId, {});

    expect(state.id).toBe("panel-456");
    expect(state.manifest.elementTag).toBe("scada-chart");
    expect(state.manifest.label).toBe("Chart View");
    expect(state.componentProps).toEqual({ seriesId: "S1" });
  });
});
