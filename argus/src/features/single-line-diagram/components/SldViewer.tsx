/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component } from "solid-js";
import { SldProvider } from "../providers/SldProvider";
import { SldHeader } from "./SldHeader";
import { SldCanvas } from "./SldCanvas";
import { SldControls } from "./SldControls";

interface SldViewerProps {
  equipmentId: string;
}

export const SldViewer: Component<SldViewerProps> = (props) => {
  return (
    <SldProvider equipmentId={props.equipmentId}>
      <div class="relative w-full h-full flex flex-col bg-bg overflow-hidden">
        <SldHeader />

        <div class="relative flex-1 w-full min-h-0 z-0 group">
          <SldCanvas />
          <SldControls />
        </div>
      </div>
    </SldProvider>
  );
};
