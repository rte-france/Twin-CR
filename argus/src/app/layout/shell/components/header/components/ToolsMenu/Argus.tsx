/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount } from "solid-js";
import { Menubar } from "@kobalte/core/menubar";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { WebviewWindow } from "@tauri-apps/api/webviewWindow";
import type { Component } from "solid-js";
import { useNavigate } from "@solidjs/router";

import { openInCentral } from "@/utils/openInCentral";

export const Argus: Component = () => {
  const [appWindow, setAppWindow] = createSignal<WebviewWindow | null>(null);
  const navigate = useNavigate();

  onMount(() => {
    const window = getCurrentWindow() as WebviewWindow;
    setAppWindow(window);
  });

  const handleClose = async () => {
    const win = appWindow();
    if (win) {
      try {
        await win.close();
      } catch (_error) {
        // Handle error silently
      }
    }
  };

  const handleSettings = () => {
    openInCentral({
      id: "settings",
      title: "Settings",
      elementTag: "panel-settings",
    });
  };

  const handleExtensions = () => {
    openInCentral({
      id: "extensions",
      title: "Extensions",
      elementTag: "panel-extensions",
    });
  };

  const handleKeymaps = () => {
    openInCentral({
      id: "keymaps",
      title: "Keymaps",
      elementTag: "panel-keymaps",
    });
  };

  const itemClass =
    "px-3 py-1.5 text-xs text-fg hover:bg-sidebar-active-bg hover:text-sidebar-active outline-none cursor-default flex justify-between items-center transition-colors";
  const separatorClass = "h-px bg-divider my-1 mx-2";

  return (
    <Menubar.Menu>
      <Menubar.Trigger class="px-3 py-1 hover:bg-fg/10 rounded-sm outline-none cursor-default text-fg text-xs transition-colors">
        Twin-CR
      </Menubar.Trigger>

      <Menubar.Portal>
        <Menubar.Content class="bg-popover-bg border border-popover-border min-w-40 py-1 shadow-lg z-50 animate-in fade-in zoom-in-95 duration-100">
          <Menubar.Item class={itemClass}>
            About Twin-CR
          </Menubar.Item>

          <Menubar.Item class={itemClass}>Check for Updates</Menubar.Item>

          <Menubar.Item class={itemClass} onSelect={() => navigate("/")}>
            Go to Workspace
          </Menubar.Item>

          <Menubar.Separator class={separatorClass} />

          <Menubar.Item class={itemClass} onSelect={handleSettings}>
            Settings
          </Menubar.Item>

          <Menubar.Item class={itemClass} onSelect={handleKeymaps}>
            Keymaps
          </Menubar.Item>

          <Menubar.Separator class={separatorClass} />

          <Menubar.Item class={itemClass} onSelect={handleExtensions}>
            Extensions
          </Menubar.Item>

          <Menubar.Separator class={separatorClass} />

          <Menubar.Item class={itemClass} onSelect={handleClose}>
            Quit
          </Menubar.Item>
        </Menubar.Content>
      </Menubar.Portal>
    </Menubar.Menu>
  );
};
