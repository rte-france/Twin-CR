/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { useLayout } from "../../providers/LayoutProvider";
import { onMount, onCleanup } from "solid-js";
import { DockviewBottom } from "../dockview/DockviewBottom";

export const BottomPanel = () => {
  const layout = useLayout();

  const isVisible = () => layout.isOpen("bottom");

  onMount(() => {
    const handleEmpty = () => layout.setActiveId("bottom", null);
    window.addEventListener("argus:bottom-empty", handleEmpty);

    onCleanup(() => {
      window.removeEventListener("argus:bottom-empty", handleEmpty);
    });
  });

  return (
    <div
      style={{
        height: `${layout.state.bottom.size}px`,
        display: isVisible() ? "flex" : "none",
      }}
      class="relative shrink-0 flex-col w-full bg-sidebar-bg border-t border-border"
    >
      <div
        onMouseDown={() => {
          const onMove = (me: MouseEvent) => {
            layout.setDim("bottom", window.innerHeight - me.clientY - 24);
          };
          window.addEventListener("mousemove", onMove);
          window.addEventListener(
            "mouseup",
            () => window.removeEventListener("mousemove", onMove),
            { once: true },
          );
        }}
        class="absolute top-0 left-0 right-0 h-2 -mt-1 cursor-row-resize hover:bg-sidebar-active/40 z-50 transition-colors"
      />

      <div class="flex-1 w-full relative overflow-hidden">
        <DockviewBottom />
      </div>
    </div>
  );
};
