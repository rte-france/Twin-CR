/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component } from "solid-js";
import { NadProvider } from "./NadContext";
import { NadMenuBar } from "./NadMenuBar";
import { NadCanvas } from "./NadCanvas";
import { EditorProvider } from "./EditorContext";

import "../editor.css";
import { Nad } from "../types";

const NadApp: Component = () => {
  return (
    <div class="flex flex-col w-full h-full min-h-0 bg-[var(--bg)] text-[var(--fg)] font-sans overflow-hidden">
      <NadMenuBar />
      <div class="flex-1 flex flex-col relative w-full min-h-0 overflow-hidden">
        <NadCanvas />
      </div>
    </div>
  );
};

export const NadViewer: Component<Nad> = (
  props,
) => {
  return (
    <NadProvider {...props}>
      <EditorProvider>
        <NadApp />
      </EditorProvider>
    </NadProvider>
  );
};
