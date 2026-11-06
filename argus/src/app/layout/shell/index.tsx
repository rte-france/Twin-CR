/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { ShellProvider } from "./providers/ShellProvider";
import { Header } from "./components/header";
import { LeftPanel } from "./components/panels/LeftPanel";
import { RightPanel } from "./components/panels/RightPanel";
import { CentralPanel } from "./components/panels/CentralPanel";
import { Footer } from "./components/footer";
import { ThemeProvider } from "./providers/ThemeProvider";
import { LayoutProvider } from "./providers/LayoutProvider";

import "./styles/shell.css";
import "./styles/dockview.css";
import { HeaderProvider } from "./providers/HeaderProvider";
import { PlacementProvider } from "./providers/PlacementProvider";

function ShellLayout() {
  return (
    <div class="h-screen w-screen flex flex-col bg-bg text-fg overflow-hidden">
      <HeaderProvider>
        <Header />
      </HeaderProvider>

      <div class="flex-1 flex overflow-hidden">
        <LeftPanel />

        <main class="flex-1 flex flex-col min-w-0 bg-bg">
          <CentralPanel />
        </main>

        <RightPanel />
      </div>

      <Footer />
    </div>
  );
}

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
