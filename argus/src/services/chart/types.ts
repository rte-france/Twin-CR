/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface ChartDataRow {
  id: string;
  topic: string;
  factor?: number;
  equipmentId?: string;
  kind: string;
  voltage_level?: string;
  substation?: string;
  isEstim?: boolean;
  side?: string | null;
}
