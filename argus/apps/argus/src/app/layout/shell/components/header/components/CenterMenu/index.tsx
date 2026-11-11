/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { ModeStatus } from "@/features/mode-settings";
import { LayoutSelect } from "./LayoutSelect";
import { useAppMode } from "@/hooks/useAppMode";
import { Show } from "solid-js";
import { GmControls } from "@/features/gm-settings";
import { Mode } from "@/services/app-mode";

export const CentralMenu = () => {
  const [mode] = useAppMode();

  return (
    <div class="inline-flex items-center gap-1.5 px-2 py-0.5 h-6 text-[10px] bg-bg/80 backdrop-blur-md rounded-md border border-border shadow-sm transition-all hover:border-border-hover hover:shadow-md">
      <div class="flex items-center gap-1.5 h-full">
        <LayoutSelect />

        <div class="w-px h-2.5 bg-divider rounded-full" />

        <ModeStatus />

        <Show when={mode() === Mode.GameMaster}>
          <div class="w-px h-2.5 bg-divider rounded-full" />
          <GmControls />
        </Show>
      </div>
    </div>
  );
};
