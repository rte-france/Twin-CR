/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { backendPost } from "@/services/backend/service";
import { ControllabilityMap } from "../types";
import { toControlKind } from "../columnMapping";

export function useControllability() {
  const [controllability, setControllability] = createSignal<ControllabilityMap>({});

  const checkControllability = async (equipmentIds: string[], columns: string[]) => {
    if (equipmentIds.length === 0 || columns.length === 0) return;
    try {
      const mappedColumns = [...new Set(columns.map(toControlKind))];
      const result = await backendPost<ControllabilityMap>("/control-batch-check", {
        equipmentIds,
        columns: mappedColumns,
      });

      const remapped: ControllabilityMap = {};
      for (const [equipmentId, kinds] of Object.entries(result)) {
        remapped[equipmentId] = columns.filter((col) => kinds.includes(toControlKind(col)));
      }
      setControllability(remapped);
    } catch (e) {
      console.error("Failed to check controllability", e);
    }
  };

  const isControllable = (equipmentId: string, column: string): boolean =>
    controllability()[equipmentId]?.includes(column) ?? false;

  return { checkControllability, isControllable };
}
