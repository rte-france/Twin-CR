/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { FiMenu } from "solid-icons/fi";
import { Component } from "solid-js";

export const LeftMenu: Component<{
  onOpenMenus: () => void;
}> = (props) => {
  return (
    <div class="flex items-center gap-x-4 pl-1">
      <div
        class="text-[11px] text-fg/60 hover:bg-fg/10 hover:text-fg py-1 rounded cursor-pointer transition-colors outline-none focus:outline-none"
        onClick={() => props.onOpenMenus()}
      >
        <FiMenu size={16} />
      </div>
    </div>
  );
};
