/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { GmStatus } from "@/features/gm-settings";
import { ScadaStatus } from "@/features/scada-settings";
import { DslStatus } from "@/features/dsl-terminal";
import { LobbyStatus } from "@/features/lobby-settings";

export const Footer = () => {
  return (
    <footer class="h-6 bg-sidebar-bg border-t border-border text-sidebar-fg flex items-center justify-between px-3 text-[10px] shrink-0 z-30">
      <div class="flex items-center gap-4 h-full">
        <GmStatus />
        <ScadaStatus />
        <DslStatus />
        <LobbyStatus />
      </div>
    </footer>
  );
};
