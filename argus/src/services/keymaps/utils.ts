/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type {
  CommandDefinition,
  KeymapNode,
  KeymapTree,
} from "@/types/keymap.type";

export const isMac =
  typeof window !== "undefined" &&
  navigator.userAgent.toLowerCase().includes("mac");

export const SPECIAL_KEYS: Record<string, string> = {
  " ": "space",
  backtab: "tab",
};

export const MODIFIER_NAMES = [
  "control",
  "meta",
  "shift",
  "alt",
  "mod",
  "ctrl",
  "os",
];

export function getEventString(
  e: KeyboardEvent | MouseEvent,
  layoutMode: "logical" | "physical" = "logical",
): string {
  const keys: string[] = [];

  if (isMac && e.metaKey) keys.push("mod");
  if (!isMac && e.ctrlKey) keys.push("mod");
  if (e.shiftKey) keys.push("shift");
  if (e.altKey) keys.push("alt");
  if (isMac && e.ctrlKey) keys.push("ctrl");
  if (!isMac && e.metaKey) keys.push("meta");

  if (e instanceof MouseEvent) {
    if (e.button === 0) keys.push("click_left");
    else if (e.button === 1) keys.push("click_middle");
    else if (e.button === 2) keys.push("click_right");
    else keys.push(`click_${e.button}`);

    return keys.join("+");
  }

  if (e.key && e.key.toLowerCase() === "dead") return "";

  let rawKey = "";
  if (layoutMode === "physical") {
    if (e.code.startsWith("Key"))
      rawKey = e.code.replace("Key", "").toLowerCase();
    else if (e.code.startsWith("Digit"))
      rawKey = e.code.replace("Digit", "").toLowerCase();
    else rawKey = e.code.toLowerCase();
  } else {
    // Standard key lookup with fallback to e.code when the browser cannot resolve the key symbol
    const keyLower = e.key ? e.key.toLowerCase() : "";
    if (!keyLower || keyLower === "unidentified") {
      rawKey = e.code ? e.code.toLowerCase() : "";
    } else {
      rawKey = keyLower;
    }
  }

  if (!rawKey) return "";

  const finalKey = SPECIAL_KEYS[rawKey] || rawKey;
  const isModifierOnly = MODIFIER_NAMES.some((mod) => finalKey.includes(mod));

  if (!isModifierOnly) {
    keys.push(finalKey);
  }

  return keys.join("+");
}

export function isInputElement(target: HTMLElement | null): boolean {
  if (!target) return false;
  return (
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.isContentEditable
  );
}

export function checkIsModifierOnly(pressedKeyStr: string): boolean {
  return ["control", "meta", "shift", "alt", "mod", "ctrl"].includes(
    pressedKeyStr,
  );
}

export function flattenKeymaps(
  tree: KeymapTree,
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
