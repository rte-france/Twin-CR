/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createLogService } from "@/utils/createLogService";

export interface TimelineEvent {
  message: string;
  modelName: string;
  time: number;
}

export const TimelineService = createLogService<TimelineEvent>({
  historyEndpoint: "/history-dynawo-timeline/",
  sseEndpoint: "/sub-dynawo-timeline",
  getKey: (e) => `${e.time}-${e.modelName}-${e.message}`,
});
