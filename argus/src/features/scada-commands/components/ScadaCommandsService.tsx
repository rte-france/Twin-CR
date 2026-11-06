/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createLogService } from "@/utils/createLogService";

export interface ScadaCommandEvent {
  command: string;
  command_source: string;
  time: number;
}

export const ScadaCommandsService = createLogService<ScadaCommandEvent>({
  historyEndpoint: "/history-scada-commands",
  sseEndpoint: "/sub-scada-commands",
  getKey: (e) => `${e.time}-${e.command_source}-${e.command}`,
});
