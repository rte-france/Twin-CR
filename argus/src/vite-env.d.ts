/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

/// <reference types="vite/client" />
import "solid-js";

declare module "solid-js" {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: `react-${string}`]: solid.JSX.HTMLAttributes<HTMLElement> & {
        "prop:mfeProps"?: any;
      };
      "iconify-icon": {
        icon: string;
        style?: any;
        class?: string;
        width?: string | number;
        height?: string | number;
        flip?: string;
        rotate?: string | number;
        mode?: "svg" | "css" | "mask";
      };
    }
  }
}
