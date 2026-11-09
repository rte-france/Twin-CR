/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Menubar } from "@kobalte/core/menubar";
import { Effect } from "effect";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { WindowBootstrapper } from "@/services/window-bootstrap";
import type { Component } from "solid-js";

export const File: Component = () => {
  const handleNewParent = () => {
    const program = WindowBootstrapper.pipe(
      Effect.flatMap((wb) => wb.createParent("Twin-CR", "/home")),
    );

    getSystemRuntime().runPromise(program).catch(console.error);
  };

  const itemClass =
    "px-3 py-1.5 text-xs text-fg hover:bg-sidebar-active-bg hover:text-sidebar-active outline-none cursor-default flex justify-between items-center transition-colors";
  const contentClass =
    "bg-popover-bg border border-popover-border min-w-40 py-1 shadow-lg z-50 animate-in fade-in zoom-in-95 duration-100 outline-none";

  return (
    <Menubar.Menu>
      <Menubar.Trigger class="px-3 py-1 hover:bg-fg/10 rounded-sm outline-none cursor-default text-fg text-xs transition-colors">
        File
      </Menubar.Trigger>

      <Menubar.Portal>
        <Menubar.Content class={contentClass}>
          <Menubar.Item class={itemClass} onSelect={handleNewParent}>
            Open Workspace
          </Menubar.Item>
        </Menubar.Content>
      </Menubar.Portal>
    </Menubar.Menu>
  );
};
