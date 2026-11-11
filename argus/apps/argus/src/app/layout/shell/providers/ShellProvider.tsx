/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { ShellContext } from "@/providers/ShellContext";
import type { ShellContextType } from "@/types";
import { createSignal, createEffect, type JSX } from "solid-js";

export function ShellProvider(props: {
  children: JSX.Element;
  windowLabel: string;
}) {
  const STORAGE_KEY = `argus-shell-layout-${props.windowLabel}`;

  const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");

  const [openStates, setOpenStates] = createSignal({
    "left-panel": saved.leftOpen ?? true,
    "right-panel": saved.rightOpen ?? false,
    "bottom-panel": saved.bottomOpen ?? true,
  });

  const [dimensions, setDimensions] = createSignal({
    "left-panel": saved.leftWidth ?? 260,
    "right-panel": saved.rightWidth ?? 260,
    "bottom-panel": saved.bottomHeight ?? 200,
  });

  createEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        leftOpen: openStates()["left-panel"],
        rightOpen: openStates()["right-panel"],
        bottomOpen: openStates()["bottom-panel"],
        leftWidth: dimensions()["left-panel"],
        rightWidth: dimensions()["right-panel"],
        bottomHeight: dimensions()["bottom-panel"],
      }),
    );
  });

  const api: ShellContextType = {
    isOpen: (id) => openStates()[id],
    dim: (id) => dimensions()[id],
    toggle: (id) => setOpenStates((p) => ({ ...p, [id]: !p[id] })),
    setDim: (id, value) => setDimensions((p) => ({ ...p, [id]: value })),
  };

  return (
    <ShellContext.Provider value={api}>{props.children}</ShellContext.Provider>
  );
}
