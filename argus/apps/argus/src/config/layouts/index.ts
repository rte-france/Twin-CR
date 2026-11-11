/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { Mode } from "@/services/app-mode";

import * as gameMaster from "./game-master";
import * as scada from "./scada";

export const layoutConfigs: Record<Mode, typeof gameMaster> = {
  GameMaster: gameMaster,
  Scada: scada,
};
