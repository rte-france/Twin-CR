/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { LaidEvent, PAD_L, TimelineEvent } from "./types";

export function capitalizeFirstLetter(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function parseTime(s?: string | number): number | null {
  if (s == null) return null;
  if (typeof s === "number") return s;
  const str = String(s).trim().toUpperCase();
  const m = str.match(/^T\+(?:(\d+):)?(\d{1,2}):(\d{2})$/);
  if (!m) return isNaN(parseFloat(str)) ? null : parseFloat(str);
  if (m[1]) {
    return (
      parseInt(m[1], 10) * 3600 + parseInt(m[2], 10) * 60 + parseInt(m[3], 10)
    );
  }
  return parseInt(m[2], 10) * 60 + parseInt(m[3], 10);
}

export function fmtTime(secs: number): string {
  if (secs < 0) secs = 0;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = Math.floor(secs % 60);
  if (h > 0) {
    return `T+${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `T+${m}:${String(s).padStart(2, "0")}`;
}

export function computeNLELayout(
  events: TimelineEvent[],
  pps: number,
): LaidEvent[] {
  const parsed = events
    .map((e) => {
      const t1 = Math.max(
        0,
        parseTime(e.type === "during" ? e.from : e.trigger) ?? 0,
      );
      let t2 = t1;
      if (e.type === "during") {
        t2 = Math.max(t1, parseTime(e.to) ?? t1 + 10);
      }
      return { ...e, t1, t2 };
    })
    .sort((a, b) => a.t1 - b.t1);

  // Greedy interval partitioning: each event goes on the lowest track free at its start. Busy tracks are kept in
  // a heap ordered by end, freed ones in a heap ordered by index, so that thousands of simultaneous events
  // (e.g. a replayed scenario) stay O(n log n) instead of scanning all the tracks for each event.
  const busy = new MinHeap<[number, number]>((a, b) => a[0] - b[0]); // [clearance end, track]
  const free = new MinHeap<number>((a, b) => a - b);
  let nTracks = 0;

  return parsed.map((ev) => {
    const xPx = PAD_L + ev.t1 * pps;
    let wPx = 0;

    if (ev.type === "during") {
      wPx = (ev.t2 - ev.t1) * pps;
    } else {
      // Les événements ponctuels s'agrandissent avec le zoom (représentation de 5 secondes visuelles)
      // avec une largeur minimum de 80px pour rester lisibles si on dézoome très loin.
      wPx = Math.max(80, 5 * pps);
    }

    if (wPx < 4) wPx = 4;

    const neededClearance = xPx + wPx + 4;
    while (busy.size() > 0 && busy.peek()![0] <= xPx) {
      free.push(busy.pop()![1]);
    }
    const track = free.size() > 0 ? free.pop()! : nTracks++;
    busy.push([neededClearance, track]);

    return { ...ev, xPx, wPx, track };
  });
}

class MinHeap<T> {
  private items: T[] = [];

  constructor(private compare: (a: T, b: T) => number) {}

  size(): number {
    return this.items.length;
  }

  peek(): T | undefined {
    return this.items[0];
  }

  push(item: T): void {
    const items = this.items;
    items.push(item);
    let i = items.length - 1;
    while (i > 0) {
      const parent = (i - 1) >> 1;
      if (this.compare(items[i], items[parent]) >= 0) break;
      [items[i], items[parent]] = [items[parent], items[i]];
      i = parent;
    }
  }

  pop(): T | undefined {
    const items = this.items;
    if (items.length === 0) return undefined;
    const top = items[0];
    const last = items.pop()!;
    if (items.length > 0) {
      items[0] = last;
      let i = 0;
      for (;;) {
        const left = 2 * i + 1;
        const right = left + 1;
        let smallest = i;
        if (left < items.length && this.compare(items[left], items[smallest]) < 0) smallest = left;
        if (right < items.length && this.compare(items[right], items[smallest]) < 0) smallest = right;
        if (smallest === i) break;
        [items[i], items[smallest]] = [items[smallest], items[i]];
        i = smallest;
      }
    }
    return top;
  }
}
