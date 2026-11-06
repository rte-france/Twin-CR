/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component } from "solid-js";
import { Separator } from "@kobalte/core/separator";
import { AiFillHome, AiOutlinePlus, AiOutlineMinus } from "solid-icons/ai";

import { LayerOverlay } from "./LayerOverlay";
import { LegendPanel } from "./LegendPanel";

interface MapToolsProps {
  onGoHome: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}

export const MapTools: Component<MapToolsProps> = (props) => {
  const btnClass =
    "w-6.5 h-6.5 bg-bg/85 backdrop-blur-md border border-border rounded-md text-icons flex items-center justify-center transition-colors hover:bg-(--theme-hover) hover:text-links hover:border-links shadow-sm cursor-pointer";

  return (
    <div class="flex flex-col gap-1">
      <button
        class={btnClass}
        onClick={() => props.onGoHome()}
        title="Étendue France"
      >
        <AiFillHome size={12} />
      </button>

      <Separator class="my-1 border-t border-divider mx-1" />

      <button
        class={`${btnClass} text-xl`}
        onClick={() => props.onZoomIn()}
        title="Zoom avant (+)"
      >
        <AiOutlinePlus size={12} />
      </button>

      <button
        class={`${btnClass} text-xl`}
        onClick={() => props.onZoomOut()}
        title="Zoom arrière (−)"
      >
        <AiOutlineMinus size={12} />
      </button>

      <Separator class="my-1 border-t border-divider mx-1" />

      <LayerOverlay />
      <LegendPanel />
    </div>
  );
};
