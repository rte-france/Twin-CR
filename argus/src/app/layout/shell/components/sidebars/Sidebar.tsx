/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, Show } from "solid-js";
import { Dynamic } from "solid-js/web";
import { useLayout } from "../../providers/LayoutProvider";
import { MfeLoader } from "../MfeLoader";
import { SidebarHeader } from "./SidebarHeader";
import type { PanelManifest } from "@/types";

interface SidebarProps {
  side: "left" | "right";
  topManifest?: PanelManifest;
  bottomManifest?: PanelManifest;
}

export function Sidebar(props: SidebarProps) {
  const layout = useLayout();
  const isLeft = () => props.side === "left";

  const [topHeightRatio, setTopHeightRatio] = createSignal(50);

  const startColResizing = (e: MouseEvent) => {
    e.preventDefault();
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (moveEvent: MouseEvent) => {
      const newDim = isLeft()
        ? moveEvent.clientX - 48
        : window.innerWidth - moveEvent.clientX - 48;
      if (newDim > 150 && newDim < 600) layout.setDim(props.side, newDim);
    };

    const onMouseUp = () => {
      document.body.style.cursor = "auto";
      document.body.style.userSelect = "auto";
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  const startRowResizing = (e: MouseEvent) => {
    e.preventDefault();
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";

    const container = (e.target as HTMLElement).parentElement;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();

    const onMouseMove = (moveEvent: MouseEvent) => {
      let newRatio =
        ((moveEvent.clientY - containerRect.top) / containerRect.height) * 100;
      newRatio = Math.max(10, Math.min(90, newRatio));
      setTopHeightRatio(newRatio);
    };

    const onMouseUp = () => {
      document.body.style.cursor = "auto";
      document.body.style.userSelect = "auto";
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  return (
    <Show
      when={
        (props.topManifest || props.bottomManifest) &&
        layout.state[props.side].isVisible
      }
    >
      <div
        class="h-full shrink-0 relative flex"
        style={{ width: `${layout.state[props.side].size}px` }}
      >
        <aside
          class={`w-full h-full flex flex-col bg-sidebar-bg overflow-hidden border-border ${isLeft() ? "border-r" : "border-l"}`}
        >
          <Show when={props.topManifest}>
            {(manifest) => (
              <div
                class="group/sidebar flex flex-col min-h-0 relative"
                style={{
                  height: props.bottomManifest
                    ? `${topHeightRatio()}%`
                    : "100%",
                }}
              >
                <SidebarHeader
                  id={manifest().id}
                  title={manifest().label || manifest().id}
                  side={props.side}
                />
                <div class="flex-1 overflow-auto bg-bg p-0">
                  <Show
                    when={manifest().entryUrl}
                    fallback={
                      <Dynamic
                        component={manifest().elementTag}
                        class="w-full h-full block"
                      />
                    }
                  >
                    <MfeLoader
                      manifest={manifest()}
                      componentProps={(manifest() as any).params}
                    />
                  </Show>
                </div>
              </div>
            )}
          </Show>

          <Show when={props.topManifest && props.bottomManifest}>
            <div
              onMouseDown={startRowResizing}
              class="relative w-full h-px cursor-row-resize z-20 shrink-0
                     before:content-[''] before:absolute before:inset-0 before:bg-border before:transition-all before:duration-150
                     hover:before:bg-sidebar-active hover:before:-top-[2px] hover:before:-bottom-[2px]
                     after:content-[''] after:absolute after:-top-2 after:-bottom-2 after:left-0 after:right-0"
            />
          </Show>

          <Show when={props.bottomManifest}>
            {(manifest) => (
              <div
                class="group/sidebar flex flex-col min-h-0 relative"
                style={{
                  height: props.topManifest
                    ? `${100 - topHeightRatio()}%`
                    : "100%",
                }}
              >
                <SidebarHeader
                  id={manifest().id}
                  title={manifest().label || manifest().id}
                  side={props.side}
                />
                <div class="flex-1 overflow-auto bg-bg p-0">
                  <Show
                    when={manifest().entryUrl}
                    fallback={
                      <Dynamic
                        component={manifest().elementTag}
                        class="w-full h-full block"
                      />
                    }
                  >
                    <MfeLoader
                      manifest={manifest()}
                      componentProps={(manifest() as any).params}
                    />
                  </Show>
                </div>
              </div>
            )}
          </Show>
        </aside>

        <div
          onMouseDown={startColResizing}
          class={`absolute top-0 bottom-0 w-px cursor-col-resize z-50 shrink-0
                 before:content-[''] before:absolute before:inset-0 before:transition-all before:duration-150
                 hover:before:bg-sidebar-active hover:before:-left-0.5 hover:before:-right-0.5
                 after:content-[''] after:absolute after:-left-2 after:-right-2 after:top-0 after:bottom-0
                 ${isLeft() ? "right-0" : "left-0"}`}
        />
      </div>
    </Show>
  );
}
