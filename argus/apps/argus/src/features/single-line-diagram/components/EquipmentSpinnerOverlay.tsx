/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component } from "solid-js";
import { FaSolidSpinner } from "solid-icons/fa";

interface EquipmentSpinnerProps {
  id: string;
  label?: string;
}

export const EquipmentSpinnerOverlay: Component<EquipmentSpinnerProps> = (
  props,
) => {
  return (
    <div
      class="flex items-center gap-2 px-3 py-2 rounded shadow-sm text-xs font-bold pointer-events-none"
      style={{
        background: "var(--popover-bg)",
        color: "var(--fg)",
        border: "1px solid var(--popover-border)",
        "box-shadow": "var(--popover-shadow)",
      }}
    >
      <FaSolidSpinner
        class="animate-spin text-sm"
        style={{ color: "var(--links)" }}
      />
      <span>{props.label || "Breaker toggling..."}</span>
    </div>
  );
};
