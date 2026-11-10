/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { CommandDefinition } from "@/types/keymap.type";

export interface KeymapNode {
  readonly description: string;
  readonly defaultKeys: string | readonly string[];
  readonly handler: () => void | Promise<void>;
}

export interface KeymapCategory {
  readonly [actionOrSub: string]:
    | KeymapNode
    | { readonly [action: string]: KeymapNode };
}

export interface KeymapTree {
  readonly [category: string]: KeymapCategory;
}

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
        defaultKeys: ["mod+w", "click_middle"],
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
  },
} as const satisfies KeymapTree;

export function flattenKeymaps(
  tree: KeymapTree = KEYMAPS,
  delimiter = ":",
): CommandDefinition[] {
  const commands: CommandDefinition[] = [];

  function traverse(node: unknown, path: string[]) {
    if (!node || typeof node !== "object") return;

    if ("description" in node && "handler" in node && "defaultKeys" in node) {
      const leaf = node as KeymapNode;
      const defaultKeys = Array.isArray(leaf.defaultKeys)
        ? leaf.defaultKeys
        : [leaf.defaultKeys as string];

      commands.push({
        id: path.join(delimiter),
        name: leaf.description,
        category: path.slice(0, -1).join(delimiter),
        defaultKeys,
        handler: leaf.handler,
      });
      return;
    }

    for (const [key, value] of Object.entries(node)) {
      traverse(value, [...path, key]);
    }
  }

  traverse(tree, []);
  return commands;
}
