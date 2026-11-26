/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

/**
 * The key of a curve: the id of its chart points (GmSseData.id), also used
 * as the row id in the chart editor. `isEstim` defaults to `item.isEstim`.
 */
export const getUniqueKey = (
  item: Pick<ChartDataRow, "equipmentId" | "kind" | "side" | "isEstim"> & {
    id?: string;
  },
  isEstim: boolean = !!item.isEstim,
) => {
  const eqId = item.equipmentId || "";
  const suffix = isEstim ? "-estim" : "";
  return item.id
    ? `${item.id}${suffix}`
    : `${eqId}-${item.kind}-${item.side || ""}${suffix}`;
};

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
