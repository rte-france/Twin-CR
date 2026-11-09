/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount, For } from "solid-js";
import type { Component } from "solid-js";
import { Menubar } from "@kobalte/core/menubar";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { WebviewWindow } from "@tauri-apps/api/webviewWindow";

import { useTheme } from "../../../../providers/ThemeProvider";
import { useAppMode } from "@/hooks/useAppMode";
import { Mode } from "@/services/app-mode";

const THEME_OPTIONS = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "one-dark", label: "One Dark" },
  { value: "isa-101", label: "ISA 101" },
  { value: "system", label: "System" },
];

const MODES = [Mode.GameMaster, Mode.Scada];

export const View: Component = () => {
  const { theme, setTheme } = useTheme();
  const [mode, setMode] = useAppMode();

  const [isMaximized, setIsMaximized] = createSignal(false);
  const [appWindow, setAppWindow] = createSignal<WebviewWindow | null>(null);

  onMount(async () => {
    const window = getCurrentWindow() as WebviewWindow;
    setAppWindow(window);
    try {
      const maximized = await window.isMaximized();
      setIsMaximized(maximized);
    } catch (_error) {}
  });

  const handleMinimize = async () => {
    const win = appWindow();
    if (win) {
      try {
        await win.minimize();
      } catch (_error) {}
    }
  };

  const handleMaximize = async () => {
    const win = appWindow();
    if (win) {
      try {
        await win.toggleMaximize();
        const maximized = await win.isMaximized();
        setIsMaximized(maximized);
      } catch (_error) {}
    }
  };

  const itemClass =
    "relative px-3 py-1.5 text-xs text-fg hover:bg-sidebar-active-bg hover:text-sidebar-active outline-none cursor-default flex justify-between items-center transition-colors";
  const separatorClass = "h-px bg-divider my-1 mx-2";
  const contentClass =
    "bg-popover-bg border border-popover-border min-w-40 py-1 shadow-lg z-50 animate-in fade-in zoom-in-95 duration-100 outline-none";

  return (
    <Menubar.Menu>
      <Menubar.Trigger class="px-3 py-1 hover:bg-fg/10 rounded-sm outline-none cursor-default text-fg text-xs transition-colors">
        View
      </Menubar.Trigger>

      <Menubar.Portal>
        <Menubar.Content class={contentClass}>
          <Menubar.Sub>
            <Menubar.SubTrigger class={itemClass}>
              Select Theme
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
                <Menubar.RadioGroup
                  value={theme()}
                  onChange={(value) => setTheme(value as any)}
                >
                  <For each={THEME_OPTIONS}>
                    {(t) => (
                      <Menubar.RadioItem value={t.value} class={itemClass}>
                        <Menubar.ItemIndicator class="absolute left-2 flex items-center justify-center">
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="10"
                            height="10"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <circle cx="12" cy="12" r="6"></circle>
                          </svg>
                        </Menubar.ItemIndicator>
                        <span class="pl-4">{t.label}</span>
                      </Menubar.RadioItem>
                    )}
                  </For>
                </Menubar.RadioGroup>
              </Menubar.SubContent>
            </Menubar.Portal>
          </Menubar.Sub>

          <Menubar.Sub>
            <Menubar.SubTrigger class={itemClass}>
              Mode
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
                <Menubar.RadioGroup
                  value={mode()}
                  onChange={(value) => setMode(value as Mode)}
                >
                  <For each={MODES}>
                    {(m) => (
                      <Menubar.RadioItem value={m} class={itemClass}>
                        <Menubar.ItemIndicator class="absolute left-2 flex items-center justify-center">
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="10"
                            height="10"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <circle cx="12" cy="12" r="6"></circle>
                          </svg>
                        </Menubar.ItemIndicator>
                        <span class="pl-4">{m}</span>
                      </Menubar.RadioItem>
                    )}
                  </For>
                </Menubar.RadioGroup>
              </Menubar.SubContent>
            </Menubar.Portal>
          </Menubar.Sub>

          <Menubar.Separator class={separatorClass} />

          <Menubar.Item
            class={itemClass}
            onSelect={() => window.location.reload()}
          >
            Reload <span class="text-fg/40 ml-4">⌘R</span>
          </Menubar.Item>

          <Menubar.Separator class={separatorClass} />

          <Menubar.Item class={itemClass} onSelect={handleMaximize}>
            {isMaximized() ? "Windowed" : "Fullscreen"}
          </Menubar.Item>

          <Menubar.Item class={itemClass} onSelect={handleMinimize}>
            Reduce
          </Menubar.Item>
        </Menubar.Content>
      </Menubar.Portal>
    </Menubar.Menu>
  );
};
