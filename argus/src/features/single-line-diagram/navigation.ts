/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { openInCentral } from "@/utils/openInCentral";
import { getEquipmentLocation } from "@/services/network";

export type SldType = "sub" | "vl";

/** Open the single line diagram of a substation or voltage level, or focus it if already open (same tab id) */
export const openSld = (equipmentId: string, type: SldType) => {
  openInCentral({
    id: `${type} - ${equipmentId}`,
    title: `${type} - ${equipmentId}`,
    elementTag: "sld-viewer",
    params: { equipmentId, type },
  });
};

/**
 * Open the substation diagram of an equipment (at its side, for a branch), located in the network of the current
 * backend, else of 'fallbackSubstationId'. Returns false if neither is known.
 */
export const openEquipmentSld = async (equipmentId: string | undefined, side?: string,
                                       fallbackSubstationId?: string) => {
  let substationId = fallbackSubstationId;
  if (equipmentId) {
    try {
      substationId = (await getEquipmentLocation(equipmentId, side)).substation_id;
    } catch (e) {
      console.warn(`No location for ${equipmentId}`, e);
    }
  }
  if (!substationId) return false;
  openSld(substationId, "sub");
  return true;
};
