/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

const COLUMN_TO_CONTROL_KIND: Record<string, string> = {
  target_p: "P",
  target_q: "Q",
  target_v: "V",
  open: "state",
};

export function toControlKind(column: string): string {
  return COLUMN_TO_CONTROL_KIND[column] ?? column;
}

// For DSL commands — open stays open, others still mapped
export function toDslKind(column: string): string {
  if (column === "open") return column;
  return COLUMN_TO_CONTROL_KIND[column] ?? column;
}
