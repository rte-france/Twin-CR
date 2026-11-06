/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { Component } from "solid-js";

interface Props {
  ref: (el: HTMLDivElement) => void;
}
export const MapGrid: Component<Props> = (props) => {
  return (
    <div
      ref={props.ref}
      class="absolute inset-0 map-canvas"
      style={{
        "background-color": "var(--bg)",
        "background-image": `
            linear-gradient(to right, color-mix(in srgb, var(--links) 15%, transparent) 1px, transparent 1px),
            linear-gradient(to bottom, color-mix(in srgb, var(--links) 15%, transparent) 1px, transparent 1px)
          `,
        "background-size": "12px 12px",
        "background-position": "center center",
      }}
    />
  );
};
