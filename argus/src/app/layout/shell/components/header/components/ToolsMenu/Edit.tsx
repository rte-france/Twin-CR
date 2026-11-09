/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Menubar } from "@kobalte/core/menubar";
import type { Component } from "solid-js";

export const Edit: Component = () => {
  const itemClass =
    "px-3 py-1.5 text-xs text-fg hover:bg-sidebar-active-bg hover:text-sidebar-active outline-none cursor-default flex justify-between items-center transition-colors";
  const separatorClass = "h-px bg-divider my-1 mx-2";
  const contentClass =
    "bg-popover-bg border border-popover-border min-w-40 py-1 shadow-lg z-50 animate-in fade-in zoom-in-95 duration-100 outline-none";

  return (
    <Menubar.Menu>
      <Menubar.Trigger class="px-3 py-1 hover:bg-fg/10 rounded-sm outline-none cursor-default text-fg text-xs transition-colors">
        Edit
      </Menubar.Trigger>

      <Menubar.Portal>
        <Menubar.Content class={contentClass}>
          <Menubar.Item class={itemClass}>
            Undo <span class="text-fg/40 ml-4">⌘Z</span>
          </Menubar.Item>

          <Menubar.Item class={itemClass}>
            Redo <span class="text-fg/40 ml-4">⇧⌘Z</span>
          </Menubar.Item>

          <Menubar.Separator class={separatorClass} />

          <Menubar.Sub>
            <Menubar.SubTrigger class={itemClass}>
              Find
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                class="ml-auto"
              >
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </Menubar.SubTrigger>

            <Menubar.Portal>
              <Menubar.SubContent class={contentClass}>
                <Menubar.Item class={itemClass}>Search the web</Menubar.Item>
                <Menubar.Separator class={separatorClass} />
                <Menubar.Item class={itemClass}>Find...</Menubar.Item>
                <Menubar.Item class={itemClass}>Find Next</Menubar.Item>
                <Menubar.Item class={itemClass}>Find Previous</Menubar.Item>
              </Menubar.SubContent>
            </Menubar.Portal>
          </Menubar.Sub>

          <Menubar.Separator class={separatorClass} />

          <Menubar.Item class={itemClass}>Cut</Menubar.Item>
          <Menubar.Item class={itemClass}>Copy</Menubar.Item>
          <Menubar.Item class={itemClass}>Paste</Menubar.Item>
        </Menubar.Content>
      </Menubar.Portal>
    </Menubar.Menu>
  );
};
