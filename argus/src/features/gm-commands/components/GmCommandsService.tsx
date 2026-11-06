/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createLogService } from "@/utils/createLogService";

export interface GmCommandEvent {
  command: string;
  command_source: string;
  time: number;
}

export const GmCommandsService = createLogService<GmCommandEvent>({
  historyEndpoint: "/history-gm-commands",
  sseEndpoint: "/sub-gm-commands",
  getKey: (e) => `${e.time}-${e.command_source}-${e.command}`,
});
