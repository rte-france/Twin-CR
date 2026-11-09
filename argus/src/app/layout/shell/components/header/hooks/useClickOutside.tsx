/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { onCleanup, onMount } from "solid-js";

export function useClickOutside(
  el: () => HTMLElement | undefined,
  callback: () => void,
) {
  const onClick = (e: MouseEvent) => {
    const target = e.target as Node;
    const currentEl = el();
    if (currentEl && !currentEl.contains(target)) {
      callback();
    }
  };

  onMount(() => {
    document.addEventListener("pointerdown", onClick);
  });

  onCleanup(() => {
    document.removeEventListener("pointerdown", onClick);
  });
}
