/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { DockviewComponent } from "dockview-core";
import {
  setIsLeftOpen,
  setIsRightOpen,
} from "./components/panels/BottomPanel/utils";

let dockviewInstance: DockviewComponent | null = null;
let leftToggleHandler: (() => void) | null = null;
let rightToggleHandler: (() => void) | null = null;

export const setDockviewInstance = (dv: DockviewComponent | null) => {
  dockviewInstance = dv;
};

export const setLeftToggleHandler = (fn: (() => void) | null) => {
  leftToggleHandler = fn;
};

export const setRightToggleHandler = (fn: (() => void) | null) => {
  rightToggleHandler = fn;
};

export const closeActivePanel = () => {
  const activeGroup = dockviewInstance?.activeGroup;
  if (activeGroup && activeGroup.activePanel) {
    activeGroup.activePanel.api.close();
  }
};

export const nextTab = () => {
  const group = dockviewInstance?.activeGroup;
  if (!group || group.panels.length <= 1) return;

  const currentIndex = group.panels.findIndex((p) => p === group.activePanel);
  const nextIndex = (currentIndex + 1) % group.panels.length;
  group.panels[nextIndex].api.setActive();
};

export const prevTab = () => {
  const group = dockviewInstance?.activeGroup;
  if (!group || group.panels.length <= 1) return;

  const currentIndex = group.panels.findIndex((p) => p === group.activePanel);
  const prevIndex =
    (currentIndex - 1 + group.panels.length) % group.panels.length;
  group.panels[prevIndex].api.setActive();
};

export const toggleMaximize = () => {
  const activeGroup = dockviewInstance?.activeGroup;
  if (activeGroup) {
    if (activeGroup.api.isMaximized()) {
      activeGroup.api.exitMaximized();
    } else {
      activeGroup.api.maximize();
    }
  }
};

export const focusGroupDirection = (
  direction: "left" | "right" | "above" | "below",
) => {
  if (!dockviewInstance || dockviewInstance.groups.length <= 1) return;

  const currentGroup = dockviewInstance.activeGroup;
  if (!currentGroup?.element) return;

  const currentRect = currentGroup.element.getBoundingClientRect();
  const currentCenter = {
    x: currentRect.left + currentRect.width / 2,
    y: currentRect.top + currentRect.height / 2,
  };

  let bestGroup: typeof currentGroup | null = null;
  let minDistance = Infinity;

  for (const group of dockviewInstance.groups) {
    if (group === currentGroup || !group.element) continue;

    const rect = group.element.getBoundingClientRect();
    const center = {
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2,
    };

    const dx = center.x - currentCenter.x;
    const dy = center.y - currentCenter.y;

    let isValid = false;
    switch (direction) {
      case "left":
        isValid = dx < -10;
        break;
      case "right":
        isValid = dx > 10;
        break;
      case "above":
        isValid = dy < -10;
        break;
      case "below":
        isValid = dy > 10;
        break;
    }

    if (isValid) {
      const distance = dx * dx + dy * dy;
      if (distance < minDistance) {
        minDistance = distance;
        bestGroup = group;
      }
    }
  }

  bestGroup?.focus();
};

export const focusGroupLeft = () => focusGroupDirection("left");
export const focusGroupRight = () => focusGroupDirection("right");
export const focusGroupAbove = () => focusGroupDirection("above");
export const focusGroupBelow = () => focusGroupDirection("below");

export const toggleLeftPanel = () => {
  leftToggleHandler?.();
};

export const toggleRightPanel = () => {
  rightToggleHandler?.();
};

export const toggleLeftBottomPanel = () => {
  setIsLeftOpen((prev) => !prev);
};

export const toggleRightBottomPanel = () => {
  setIsRightOpen((prev) => !prev);
};
