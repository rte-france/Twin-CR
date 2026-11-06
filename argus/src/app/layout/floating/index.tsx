/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { ThemeProvider } from "../shell/providers/ThemeProvider";
import type { JSX } from "solid-js";

export function FloatingLayout(props: {
  windowLabel: string;
  themeSyncId: string;
  children: JSX.Element;
}) {
  return (
    <ThemeProvider syncId={props.themeSyncId}>
      <div class="h-screen w-screen bg-bg text-fg flex flex-col overflow-hidden">
        <main class="flex-1 overflow-auto">{props.children}</main>
      </div>
    </ThemeProvider>
  );
}
