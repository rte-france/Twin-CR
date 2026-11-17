/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { formatTimeHHMMSS } from "@/utils/formatTimeHHMMSS";
import { openEquipmentSld } from "@/features/single-line-diagram/navigation";

/** Text colour of the alarm colours of the alarm config (e.g. yellow < red < violet, blue/grey for breaker opening/closing) */
const COLORS: Record<string, string> = {
  grey: "#9ca3af",
  blue: "#38bdf8",
  yellow: "#eab308",
  red: "#ef4444",
  violet: "#d946ef",
};

export const alarmColor = (color: string | undefined) => (color && COLORS[color]) || color || "var(--fg)";

export const formatAlarmTime = (time: number | undefined) => (time != null ? formatTimeHHMMSS(time) : "");

/** Text filter with * wildcards (e.g. *BREAKER*), case insensitive. Without wildcard: contains. */
export const textMatcher = (filter: string): ((text: string) => boolean) => {
  const trimmed = filter.trim();
  if (!trimmed) return () => true;
  if (!trimmed.includes("*")) {
    const lower = trimmed.toLowerCase();
    return (text) => text.toLowerCase().includes(lower);
  }
  const pattern = trimmed
    .split("*")
    .map((part) => part.replace(/[.+?^${}()|[\]\\]/g, "\\$&"))
    .join(".*");
  const regex = new RegExp(`^${pattern}$`, "i");
  return (text) => regex.test(text);
};

/** Parse HH:MM:SS (or seconds) into seconds, null if empty or invalid */
export const parseTime = (text: string): number | null => {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const parts = trimmed.split(":").map(Number);
  if (parts.some((p) => Number.isNaN(p))) return null;
  return parts.reduce((total, part) => total * 60 + part, 0);
};

type Locatable = { equipment_id?: string; side?: string; substation_id?: string };

export const canLocate = (row: Locatable) => !!(row.equipment_id || row.substation_id);

/**
 * Open the substation view of an alarm or event ("Locate"): the substation of its equipment (at its side, for a
 * branch) in the network of the current backend, else the substation of the alarm config.
 */
export const locate = (row: Locatable) => openEquipmentSld(row.equipment_id, row.side, row.substation_id);
