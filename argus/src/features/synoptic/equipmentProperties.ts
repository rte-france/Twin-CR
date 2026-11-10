/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { rowsOf, typeOf } from "@/services/network-properties";

/** Static properties (network tables, as in the network properties viewer) shown on hover, by component type */
const HOVER_COLUMNS: Record<string, string[]> = {
  generator: ["name", "energy_source", "max_p", "min_p"],
  voltage_level: ["name", "nominal_v"],
  line: ["name"],
  "2_windings_transformer": ["name"],
  tie_line: ["name"],
  hvdc_line: ["name", "max_p"],
};

export interface EquipmentProperties {
  type: string;
  values: [string, string | number | boolean][];
}

/** Component type and a few static properties of an equipment, for the hover card */
export const equipmentProperties = async (id: string): Promise<EquipmentProperties | null> => {
  try {
    const type = await typeOf(id);
    if (!type) return null;
    const row = (await rowsOf(type, [id]))[id] ?? {};
    const values: EquipmentProperties["values"] = [];
    for (const col of HOVER_COLUMNS[type] ?? ["name"]) {
      const v = row[col];
      if (v === null || v === undefined || v === "" || (typeof v === "number" && !Number.isFinite(v))) continue;
      values.push([col, typeof v === "number" ? Math.round(v * 10) / 10 : v]);
    }
    return { type, values };
  } catch {
    return null;
  }
};
