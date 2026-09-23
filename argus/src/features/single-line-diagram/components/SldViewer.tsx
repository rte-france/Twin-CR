/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component } from "solid-js";
import { SldProvider } from "../providers/SldProvider";
import type { ElementType } from "../types/ElementType";
import {
  singleElementParams,
  type SldDiagramParams,
} from "../types/SldDiagram";
import { SldHeader } from "./SldHeader";
import { SldCanvas } from "./SldCanvas";
import { SldControls } from "./SldControls";

/** A single substation or voltage level, as opened from the substation tree, the map or a line. */
interface SldElementProps {
  equipmentId: string;
  type: ElementType;
  id?: never;
  name?: never;
  params?: never;
}

/** A diagram saved in the SLD explorer, which may hold several elements and a layout. */
interface SldDiagramProps {
  id: string;
  name: string;
  params: SldDiagramParams;
  equipmentId?: never;
  type?: never;
}

type SldViewerProps = SldElementProps | SldDiagramProps;

export const SldViewer: Component<SldViewerProps> = (props) => {
  const params = () =>
    props.params !== undefined
      ? props.params
      : singleElementParams(props.equipmentId, props.type);
  const viewId = () => props.id ?? props.equipmentId;
  const label = () => props.name ?? props.equipmentId;

  return (
    <SldProvider viewId={viewId()} label={label()} params={params()}>
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
