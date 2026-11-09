/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { ShellProvider } from "./providers/ShellProvider";
import { ThemeProvider } from "./providers/ThemeProvider";
import { LayoutProvider } from "./providers/LayoutProvider";
import { PlacementProvider } from "./providers/PlacementProvider";

import { ShellLayout } from "./components/ShellLayout";

import "./styles/shell.css";
import "./styles/dockview.css";

export function Shell(props: { windowLabel: string; themeSyncId: string }) {
  return (
    <ThemeProvider syncId={props.themeSyncId}>
      <LayoutProvider windowLabel={props.windowLabel}>
        <ShellProvider windowLabel={props.windowLabel}>
          <PlacementProvider>
            <ShellLayout />
          </PlacementProvider>
        </ShellProvider>
      </LayoutProvider>
    </ThemeProvider>
  );
}
