/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component } from "solid-js";
import { useSldContext } from "../providers/SldProvider";

export const SldHeader: Component = () => {
  const ctx = useSldContext();

  return (
    <header class="flex flex-wrap sm:flex-nowrap items-center justify-between px-3 sm:px-5 py-2.5 bg-sidebar-bg border-b border-border shrink-0 gap-3 min-h-9 h-9">
      <div class="flex items-center gap-3 min-w-0">
        <h2 class="text-[13px] font-bold text-fg truncate">
          Equipment: <span class="text-links">{ctx.label}</span>
        </h2>
      </div>
    </header>
  );
};
