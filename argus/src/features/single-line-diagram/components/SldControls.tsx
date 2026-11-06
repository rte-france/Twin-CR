/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, type Component } from "solid-js";
import { Separator } from "@kobalte/core/separator";
import { AiFillHome, AiOutlinePlus, AiOutlineMinus } from "solid-icons/ai";
import { FiShield, FiActivity } from "solid-icons/fi";
import { useSldContext } from "../providers/SldProvider";
import { useAppMode } from "@/hooks/useAppMode";
import { Mode } from "@/services/app-mode";

export const SldControls: Component = () => {
  const btnClass =
    "w-6.5 h-6.5 bg-bg/85 backdrop-blur-md border border-border rounded-md text-icons flex items-center justify-center transition-colors hover:bg-(--theme-hover) hover:text-links hover:border-links shadow-sm cursor-pointer";
  const btnClassActive = `${btnClass} text-links border-links`;
  const btnClassMuted = `${btnClass} opacity-40`;

  const ctx = useSldContext();
  const [mode] = useAppMode();

  return (
    <div class="absolute bottom-3.5 right-3.5 flex flex-col gap-1 z-10 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity duration-300">
      <button onClick={ctx.resetZoom} class={btnClass} title="Centrer la vue">
        <AiFillHome size={12} />
      </button>

      <Separator class="my-1 border-t border-divider mx-1" />

      <button onClick={ctx.zoomIn} class={btnClass} title="Zoom +">
        <AiOutlinePlus size={12} />
      </button>
      <button onClick={ctx.zoomOut} class={btnClass} title="Zoom -">
        <AiOutlineMinus size={12} />
      </button>

      <Separator class="my-1 border-t border-divider mx-1" />

      <button
        onClick={() => ctx.setShowProtectionLabels(!ctx.showProtectionLabels())}
        class={ctx.showProtectionLabels() ? btnClassActive : btnClassMuted}
        title={
          ctx.showProtectionLabels()
            ? "Hide protection zones"
            : "Show protection zones"
        }
      >
        <FiShield size={12} />
      </button>
      <Show when={mode() === Mode.Scada}>
        <button
          onClick={() => ctx.setShowMeasurementLabels(!ctx.showMeasurementLabels())}
          class={ctx.showMeasurementLabels() ? btnClassActive : btnClassMuted}
          title={
            ctx.showMeasurementLabels()
              ? "Hide measurements"
              : "Show measurements"
          }
        >
          <FiActivity size={12} />
        </button>
      </Show>
    </div>
  );
};
