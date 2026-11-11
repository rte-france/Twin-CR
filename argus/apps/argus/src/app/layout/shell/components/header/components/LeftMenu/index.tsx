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
    <div class="flex items-center gap-x-4">
      <button
        class="text-xs text-icons hover:text-fg hover:bg-media-bg px-1 py-1 rounded transition-colors cursor-pointer outline-none focus:ring-1 focus:ring-links"
        onClick={() => props.onOpenMenus()}
      >
        <FiMenu size={16} />
      </button>
    </div>
  );
};
