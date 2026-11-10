/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect } from "vitest";
import { flattenEventTree, registerEvents } from "@/services/events";
import { EVENTS } from "@/config/events";
import type { EventTree } from "@/types/event.type";

describe("Event Registry & registerEvents", () => {
  it("flattens an event tree with colon delimiter", () => {
    const fn1 = () => {};
    const fn2 = () => {};
    const tree: EventTree = {
      argus: {
        tab: {
          next: fn1,
          prev: fn2,
        },
      },
    };

    const result = flattenEventTree(tree);

    expect(result).toHaveLength(2);
    expect(result).toContainEqual({
      type: "argus:tab:next",
      listener: fn1,
    });
    expect(result).toContainEqual({
      type: "argus:tab:prev",
      listener: fn2,
    });
  });

  it("registers listeners and cleans them up cleanly", () => {
    let called = false;
    const cleanup = registerEvents({
      argus: {
        tab: {
          next: () => {
            called = true;
          },
        },
      },
    });

    window.dispatchEvent(new CustomEvent("argus:tab:next"));
    expect(called).toBe(true);

    called = false;
    cleanup();
    window.dispatchEvent(new CustomEvent("argus:tab:next"));
    expect(called).toBe(false);
  });

  it("contains declarative EVENTS map with correct paths", () => {
    const flattened = flattenEventTree(EVENTS);
    const types = flattened.map((f) => f.type);

    expect(types).toContain("argus:tab:next");
    expect(types).toContain("argus:tab:prev");
    expect(types).toContain("argus:group:left");
    expect(types).toContain("argus:group:right");
    expect(types).toContain("argus:group:up");
    expect(types).toContain("argus:group:down");
    expect(types).toContain("argus:panel:close");
    expect(types).toContain("argus:panel:maximize:toggle");
    expect(types).toContain("argus:panel:left:toggle");
    expect(types).toContain("argus:panel:right:toggle");
    expect(types).toContain("argus:panel:left-bottom:toggle");
    expect(types).toContain("argus:panel:right-bottom:toggle");
  });
});
