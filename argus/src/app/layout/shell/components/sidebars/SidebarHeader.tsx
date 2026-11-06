/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { FiMinus } from "solid-icons/fi";
import { type Component } from "solid-js";

interface Props {
  id: string;
  title: string;
  side: "left" | "right";
}

export const SidebarHeader: Component<Props> = (props) => {
  const handleClose = (e: MouseEvent) => {
    e.stopPropagation();
    window.dispatchEvent(
      new CustomEvent("argus:remove-panel", {
        detail: { id: props.id, side: props.side },
      }),
    );
  };

  return (
    <div class="flex w-full h-9 shrink-0 items-center justify-between px-3 bg-sidebar-bg border-b border-border">
      <div class="flex items-center min-w-0">
        <span class="text-xs uppercase font-bold text-sidebar-fg opacity-70 truncate">
          {props.title}
        </span>
      </div>
      <button
        onClick={handleClose}
        class="opacity-0 group-hover/sidebar:opacity-100 p-1 hover:bg-border rounded transition-all outline-none text-icons hover:text-icons-hover cursor-pointer"
        title="Close Panel"
      >
        <FiMinus size={15} />
      </button>
    </div>
  );
};
