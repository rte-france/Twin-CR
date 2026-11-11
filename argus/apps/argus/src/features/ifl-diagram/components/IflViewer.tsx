/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component } from "solid-js";
import { IflProvider } from "./IflContext";
import { IflMenuBar } from "./IflMenuBar";
import { IflCanvas } from "./IflCanvas";
import { IflParams } from "../types";

const IflApp: Component = () => {
  return (
    <div class="flex flex-col w-full h-full min-h-0 bg-[var(--bg)] text-[var(--fg)] font-sans overflow-hidden">
      <IflMenuBar />
      <div class="flex-1 flex flex-col relative w-full min-h-0 overflow-hidden">
        <IflCanvas />
      </div>
    </div>
  );
};

export const IflViewer: Component<IflParams> = (
  props,
) => {
  return (
    <IflProvider {...props}>
        <IflApp />
    </IflProvider>
  );
};
