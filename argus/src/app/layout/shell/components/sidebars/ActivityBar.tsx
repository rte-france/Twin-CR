/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type JSX } from "solid-js";
import { Tooltip } from "@kobalte/core/tooltip";
import { openInBottomLeft, openInBottomRight } from "@/utils/openInCentral";

export const ADD_CENTRAL_EVENT = "argus:add-central";

interface ActivityBarProps {
  id: string;
  side: "left" | "right";
  target?: "left" | "right" | "bottom";
  icon: JSX.Element;
  isActive?: boolean;
  title?: string;
  elementTag?: string;
}

export function ActivityBar(props: ActivityBarProps) {
  const targetPanel = () => props.target || props.side;

  const handleClick = () => {
    const target = targetPanel();

    if (target === "bottom") {
      if (props.side === "left") {
        openInBottomLeft({
          id: props.id,
          title: props.title || props.id,
          elementTag: props.elementTag || props.id,
        });
      } else {
        openInBottomRight({
          id: props.id,
          title: props.title || props.id,
          elementTag: props.elementTag || props.id,
        });
      }
    } else {
      window.dispatchEvent(
        new CustomEvent("argus:toggle-tool", {
          detail: { id: props.id, side: props.side },
        }),
      );
    }
  };

  return (
    <Tooltip
      openDelay={800}
      closeDelay={100}
      placement={props.side === "left" ? "right" : "left"}
    >
      <Tooltip.Trigger
        as="button"
        onClick={handleClick}
        onDragStart={(e: any) => {
          if (e.dataTransfer) {
            e.dataTransfer.setData("argus/tool-id", props.id);
            e.dataTransfer.effectAllowed = "copy";
          }
        }}
        class={`w-full h-9 flex items-center justify-center transition-colors relative cursor-pointer outline-none
        ${props.isActive ? "text-sidebar-active" : "text-icons hover:text-icons-hover hover:bg-icon-btn-bg-hover"}`}
      >
        {props.icon}
        {props.isActive && (
          <div
            class={`absolute inset-y-2 w-0.75 bg-sidebar-active rounded-full ${props.side === "left" ? "left-0" : "right-0"}`}
          />
        )}
      </Tooltip.Trigger>

      <Tooltip.Portal>
        <Tooltip.Content
          class="z-50 px-2.5 py-1.5 text-xs font-medium text-sidebar-fg bg-sidebar-bg border border-border shadow-md rounded-sm outline-none
                 origin-(--kb-tooltip-content-transform-origin)
                 data-expanded:animate-in data-closed:animate-out
                 data-expanded:fade-in-0 data-closed:fade-out-0
                 data-expanded:zoom-in-95 data-closed:zoom-out-95"
        >
          <Tooltip.Arrow class="fill-border" size={12} />
          <div
            class="absolute w-2 h-2 bg-sidebar-bg rotate-45 -z-10"
            style={{
              ...(props.side === "left"
                ? { left: "-4px", top: "calc(50% - 4px)" }
                : { right: "-4px", top: "calc(50% - 4px)" }),
            }}
          />

          <span class="relative z-10">{props.title || props.id}</span>
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip>
  );
}
