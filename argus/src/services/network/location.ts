/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { backendGet } from "@/services/backend";

/** Location of an element of the network of the current backend (GET /network/location) */
export interface EquipmentLocation {
  substation_id: string;
  voltage_level_id: string | null;  // Null for a substation
}

/**
 * Substation and voltage level of an equipment, a voltage level or a substation (including the ground disconnectors
 * and the transformers merged into three windings ones). Rejects if not found.
 * @param side side of a branch or three windings transformer (ONE, TWO or THREE, default ONE)
 */
export const getEquipmentLocation = (equipmentId: string, side?: string) =>
  backendGet<EquipmentLocation>(
    `/network/location?id=${encodeURIComponent(equipmentId)}${side ? `&side=${encodeURIComponent(side)}` : ""}`,
  );
