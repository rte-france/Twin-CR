/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Menubar } from "@kobalte/core/menubar";
import type { Component } from "solid-js";

import { Argus } from "./Argus";
import { File } from "./File";
import { View } from "./View";

export const ToolsMenu: Component = () => {
  return (
    <div class="border-b border-border bg-bg w-full h-8 flex items-center px-1">
      <Menubar class="flex space-x-1 select-none">
        <Argus />
        <File />
        <View />
      </Menubar>
    </div>
  );
};
