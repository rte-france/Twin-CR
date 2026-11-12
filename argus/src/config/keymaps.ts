/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { KeymapTree } from "@/types/keymap.type";

export const KEYMAPS = {
  application: {
    panel: {
      open_left: {
        description: "Open Left Panel",
        defaultKeys: ["mod+b"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:panel:left:toggle"));
        },
      },
      open_left_bottom: {
        description: "Open Left Bottom Panel",
        defaultKeys: ["mod+j"],
        handler: () => {
          window.dispatchEvent(
            new CustomEvent("argus:panel:left-bottom:toggle"),
          );
        },
      },
      open_right: {
        description: "Open Right Panel",
        defaultKeys: ["mod+shift+b"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:panel:right:toggle"));
        },
      },
      open_right_bottom: {
        description: "Open Right Bottom Panel",
        defaultKeys: ["mod+shift+j"],
        handler: () => {
          window.dispatchEvent(
            new CustomEvent("argus:panel:right-bottom:toggle"),
          );
        },
      },
      close_panel: {
        description: "Close Active Panel",
        defaultKeys: ["mod+w"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:panel:close"));
        },
      },
      toggle_maximize: {
        description: "Toggle Maximize Active Panel",
        defaultKeys: ["mod+m"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:panel:maximize:toggle"));
        },
      },
    },
    tab: {
      go_to_next: {
        description: "Go to Next Tab",
        defaultKeys: ["mod+tab"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:tab:next"));
        },
      },
      go_to_previous: {
        description: "Go to Previous Tab",
        defaultKeys: ["mod+shift+tab"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:tab:prev"));
        },
      },
    },
    group: {
      focus_left: {
        description: "Focus Group Left",
        defaultKeys: ["mod+arrowleft"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:group:left"));
        },
      },
      focus_right: {
        description: "Focus Group Right",
        defaultKeys: ["mod+arrowright"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:group:right"));
        },
      },
      focus_up: {
        description: "Focus Group Up",
        defaultKeys: ["mod+arrowup"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:group:up"));
        },
      },
      focus_down: {
        description: "Focus Group Down",
        defaultKeys: ["mod+arrowdown"],
        handler: () => {
          window.dispatchEvent(new CustomEvent("argus:group:down"));
        },
      },
    },
  },
} as const satisfies KeymapTree;
