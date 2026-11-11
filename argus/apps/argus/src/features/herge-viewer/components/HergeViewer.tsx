/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component } from "solid-js";
import { HergeProvider } from "../providers/HergeProvider";
import { MapCanvas } from "./MapCanvas";
import { HergeHeader } from "./HergeHeader";

import "leaflet/dist/leaflet.css";
import "../styles/index.css";

interface HergeViewerProps {
  selectedSchema?: string;
}
export const HergeViewer: Component<HergeViewerProps> = (props) => {
  return (
    <HergeProvider selectedSchema={props.selectedSchema}>
      <div class="flex flex-col h-full overflow-hidden bg-bg text-fg font-mono text-[13px] select-none">
        <HergeHeader />
        <div class="flex flex-1 overflow-hidden relative">
          <MapCanvas />
        </div>
      </div>
    </HergeProvider>
  );
};
