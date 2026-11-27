/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createMemo, Show } from "solid-js";
import { Icon } from "@iconify-icon/solid";
import { openInCentral } from "@/utils/openInCentral";
import { alarmStore, type Alarm } from "../store";
import { alarmColor } from "../display";
import { alarmsMuted } from "../sound";

export const ALARM_TOOL = {
  id: "alarms",
  title: "Alarms",
  iconId: "mdi:alarm-light-outline",
  elementTag: "alarm-list",
} as const;

/** Open the alarm window in the central dock: adds its tab, or focuses it if already open */
export const openAlarmWindow = () => openInCentral(ALARM_TOOL);

/** Header badge: number of unacknowledged alarms, in the colour of the highest priority one. Opens the alarm window. */
export const AlarmBadge = () => {
  const unacked = createMemo(() => alarmStore.alarms().filter((a) => !a.acked));
  const top = createMemo(() =>
    unacked().reduce<Alarm | undefined>((best, a) => (!best || a.priority > best.priority ? a : best), undefined),
  );

  return (
    <button
      class="flex items-center gap-1 h-full px-1 rounded hover:bg-[var(--theme-hover)] cursor-pointer"
      title={`${unacked().length} unacknowledged alarm(s) out of ${alarmStore.alarms().length}${alarmsMuted() ? " (muted)" : ""}`}
      onClick={openAlarmWindow}
    >
      <Icon icon={alarmsMuted() ? "mdi:bell-off-outline" : "mdi:bell-outline"} />
      <Show when={unacked().length > 0} fallback={<span class="opacity-60">0</span>}>
        <span class="font-bold" style={{ color: alarmColor(top()?.color) }}>
          {unacked().length}
        </span>
      </Show>
    </button>
  );
};
