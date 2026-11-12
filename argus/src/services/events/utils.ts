/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { EventTree, FlattenedEvent, EventNode } from "@/types/event.type";

function isEventNode(val: unknown): val is EventNode {
  if (typeof val === "function") return true;
  if (val && typeof val === "object") {
    if ("handleEvent" in val && typeof (val as any).handleEvent === "function") {
      return true;
    }
    if ("listener" in val && (typeof (val as any).listener === "function" || typeof (val as any).listener === "object")) {
      return true;
    }
  }
  return false;
}

export function flattenEventTree(tree: EventTree, delimiter = ":"): FlattenedEvent[] {
  const result: FlattenedEvent[] = [];

  function traverse(node: unknown, path: string[]) {
    if (isEventNode(node)) {
      if (typeof node === "function" || ("handleEvent" in node && typeof (node as any).handleEvent === "function")) {
        result.push({
          type: path.join(delimiter),
          listener: node as EventListenerOrEventListenerObject,
        });
      } else {
        result.push({
          type: path.join(delimiter),
          listener: (node as any).listener,
          options: (node as any).options,
        });
      }
      return;
    }

    if (!node || typeof node !== "object") return;

    for (const [key, value] of Object.entries(node)) {
      traverse(value, [...path, key]);
    }
  }

  traverse(tree, []);
  return result;
}
