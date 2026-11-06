/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component } from "solid-js";
import { DropdownMenu } from "@kobalte/core/dropdown-menu";
import { FiMenu, FiChevronRight } from "solid-icons/fi";
import { useIflContext } from "../hooks/useIflContext";

const triggerClass =
  "hover:bg-[var(--sidebar-active-bg)] rounded transition-colors text-[var(--fg)] opacity-80 hover:opacity-100 outline-none data-[expanded]:bg-[var(--sidebar-active-bg)] data-[expanded]:text-[var(--links)]";
const contentClass =
  "min-w-[200px] bg-[var(--popover-bg)] border border-[var(--popover-border)] rounded-md shadow-[var(--popover-shadow)] p-1 z-50 outline-none animate-in fade-in zoom-in-95 duration-100";
const itemClass =
  "relative flex items-center justify-between px-2 py-2 text-[11px] text-[var(--fg)] outline-none cursor-pointer rounded hover:bg-[var(--sidebar-active-bg)] hover:text-[var(--links)] data-[highlighted]:bg-[var(--sidebar-active-bg)] data-[highlighted]:text-[var(--links)] transition-colors data-[disabled]:opacity-40 data-[disabled]:pointer-events-none";
const subTriggerClass =
  "flex items-center justify-between w-full px-2 py-2 text-[11px] text-[var(--fg)] outline-none cursor-pointer rounded data-[highlighted]:bg-[var(--sidebar-active-bg)] data-[highlighted]:text-[var(--links)] transition-colors";
const separatorClass = "h-px bg-[var(--border)] my-1 -mx-1 opacity-50";

export const IflMenuEditor: Component = () => {
  const ctx = useIflContext();

  return (
    <DropdownMenu>
      <DropdownMenu.Trigger class={triggerClass}>
        <FiMenu size={16} />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content class={contentClass}>
          <DropdownMenu.Sub>
            <DropdownMenu.SubTrigger class={subTriggerClass}>
              Layers <FiChevronRight size={12} class="opacity-50" />
            </DropdownMenu.SubTrigger>
            <DropdownMenu.Portal>
              <DropdownMenu.SubContent class={contentClass}>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.layers.labels}
                  onChange={(c) => ctx.setLayers("labels", c)}
                >
                  Labels{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
              </DropdownMenu.SubContent>
            </DropdownMenu.Portal>
          </DropdownMenu.Sub>

          <DropdownMenu.Separator class={separatorClass} />

          <DropdownMenu.Item class={itemClass} onClick={() => ctx.resetView()}>
            Reset View
          </DropdownMenu.Item>
          <DropdownMenu.Item
            class={itemClass}
            onClick={() => ctx.fitCanvas()()}
          >
            Fit Canvas
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu>
  );
};
