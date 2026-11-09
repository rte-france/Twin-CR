/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount, onCleanup, type Component } from "solid-js";
import { DropdownMenu } from "@kobalte/core/dropdown-menu";
import { FaSolidEllipsisVertical } from "solid-icons/fa";
import type { DockviewGroupPanel } from "dockview-core";

interface LeftHeaderActionsProps {
  group: DockviewGroupPanel;
}

export const LeftHeaderActions: Component<LeftHeaderActionsProps> = (props) => {
  const [isHovered, setIsHovered] = createSignal(false);

  onMount(() => {
    const groupElement = props.group.element;
    const handleMouseEnter = () => setIsHovered(true);
    const handleMouseLeave = () => setIsHovered(false);

    if (groupElement) {
      groupElement.addEventListener("mouseenter", handleMouseEnter);
      groupElement.addEventListener("mouseleave", handleMouseLeave);
    }

    onCleanup(() => {
      if (groupElement) {
        groupElement.removeEventListener("mouseenter", handleMouseEnter);
        groupElement.removeEventListener("mouseleave", handleMouseLeave);
      }
    });
  });

  const handleCloseAll = () => {
    props.group.model.closeAllPanels();
  };

  return (
    <div
      class={`h-full flex items-center px-2 transition-opacity duration-200 ${
        isHovered() ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
    >
      <DropdownMenu>
        <DropdownMenu.Trigger class="hover:bg-icon-btn-bg-hover rounded-sm hover:text-icons-hover text-icons outline-none flex items-center justify-center p-1">
          <FaSolidEllipsisVertical />
        </DropdownMenu.Trigger>

        <DropdownMenu.Portal>
          <DropdownMenu.Content class="z-50 min-w-32 overflow-hidden rounded-md border border-popover-border bg-popover-bg p-1 text-fg shadow-md outline-none data-expanded:animate-in data-closed:animate-out data-closed:fade-out-0 data-expanded:fade-in-0 data-closed:zoom-out-95 data-expanded:zoom-in-95">
            <DropdownMenu.Item
              onSelect={handleCloseAll}
              class="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none focus:bg-theme-hover focus:text-fg data-disabled:pointer-events-none data-disabled:opacity-50"
            >
              Close All
            </DropdownMenu.Item>

            <DropdownMenu.Separator class="-mx-1 my-1 h-px bg-divider" />

            <DropdownMenu.Item class="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none focus:bg-theme-hover focus:text-fg data-disabled:pointer-events-none data-disabled:opacity-50">
              Lock Groups
            </DropdownMenu.Item>

            <DropdownMenu.Separator class="-mx-1 my-1 h-px bg-divider" />

            <DropdownMenu.Item class="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none focus:bg-theme-hover focus:text-fg data-disabled:pointer-events-none data-disabled:opacity-50">
              Detach Panel
            </DropdownMenu.Item>

            <DropdownMenu.Item class="relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none focus:bg-theme-hover focus:text-fg data-disabled:pointer-events-none data-disabled:opacity-50">
              Detach Groups
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu>
    </div>
  );
};
