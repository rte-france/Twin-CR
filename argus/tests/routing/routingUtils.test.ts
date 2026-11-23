/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect, beforeEach } from "vitest";
import { resolveInitialPath, isDetachedWindow, resetRoutingCache } from "@/app/routes/routingUtils";

describe("Routing Utilities", () => {
  beforeEach(() => {
    resetRoutingCache();
  });

  it("resolves route from query parameter when present", () => {
    window.history.replaceState({}, "", "/?parent=main&route=%2Fpanels%2Ftest-panel%3Fdetached%3Dtrue");
    expect(resolveInitialPath()).toBe("/panels/test-panel?detached=true");
  });

  it("falls back to location.pathname if route query is missing", () => {
    window.history.replaceState({}, "", "/home");
    expect(resolveInitialPath()).toBe("/home");
  });

  it("detects detached window via parent param or detached flag", () => {
    window.history.replaceState({}, "", "/?parent=main");
    expect(isDetachedWindow()).toBe(true);

    resetRoutingCache();
    window.history.replaceState({}, "", "/?detached=true");
    expect(isDetachedWindow()).toBe(true);

    resetRoutingCache();
    window.history.replaceState({}, "", "/");
    expect(isDetachedWindow()).toBe(false);
  });
});
