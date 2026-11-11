/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect, it } from "vitest";
import { computeNLELayout } from "./utils";
import type { TimelineEvent } from "./types";

/** Previous track assignment (linear scan of the tracks for each event), used as reference. */
function referenceTracks(events: TimelineEvent[], pps: number): number[] {
  const tracksEnds: number[] = [];
  return computeNLELayout(events, pps).map((ev) => {
    let track = 0;
    while (tracksEnds[track] !== undefined && tracksEnds[track] > ev.xPx) {
      track++;
    }
    tracksEnds[track] = ev.xPx + ev.wPx + 4;
    return track;
  });
}

function randomEvents(n: number, seed: number): TimelineEvent[] {
  let state = seed;
  const random = () => {
    state = (state * 1103515245 + 12345) % 2 ** 31;
    return state / 2 ** 31;
  };
  return Array.from({ length: n }, (_, i) => {
    const t = Math.floor(random() * 12) * 300 + (random() < 0.5 ? 0 : Math.floor(random() * 300)); // clusters
    return random() < 0.1
      ? { id: String(i), type: "during", from: t, to: t + random() * 200, action: "ramp" }
      : { id: String(i), type: "at", trigger: t, action: "set" };
  });
}

describe("computeNLELayout", () => {
  it("assigns the same tracks as the linear scan", () => {
    for (const pps of [1, 5, 50]) {
      const events = randomEvents(3000, pps);
      expect(computeNLELayout(events, pps).map((e) => e.track)).toEqual(referenceTracks(events, pps));
    }
  });

  it("lays out a 30k events replay scenario quickly", () => {
    const events = randomEvents(30000, 42);
    const start = performance.now();
    computeNLELayout(events, 5);
    expect(performance.now() - start).toBeLessThan(500);
  });
});
