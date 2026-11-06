/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { SubstationHeader } from "./SubstationHeader";
import { SubstationFooter } from "./SubstationFooter";
import { SubstationList } from "./SubstationList";
import { SubstationExplorerProvider } from "../providers/SubstationExplorerProvider";

export const SubstationExplorer = () => {
  return (
    <SubstationExplorerProvider>
      <div class="flex flex-col h-full bg-bg text-fg font-sans  select-none">
        <SubstationHeader />
        <SubstationList />
        <SubstationFooter />
      </div>
    </SubstationExplorerProvider>
  );
};
