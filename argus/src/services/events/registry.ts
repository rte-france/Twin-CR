/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { EventTree, FlattenedEvent } from "@/types/event.type";
import { flattenEventTree } from "./utils";

/**
 * Registers an event tree against a target (defaults to window).
 * Automatically flattens the tree keys with ":" delimiter and attaches addEventListener.
 * Returns an unregister cleanup function.
 */
export function registerEvents(
  tree: EventTree,
  target: EventTarget = window,
): () => void {
  const flattened: FlattenedEvent[] = flattenEventTree(tree);

  flattened.forEach((item) => {
    target.addEventListener(item.type, item.listener, item.options);
  });

  return () => {
    flattened.forEach((item) => {
      target.removeEventListener(item.type, item.listener, item.options);
    });
  };
}
