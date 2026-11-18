/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, createMemo, createSignal, onCleanup, onMount, Show } from "solid-js";
import { Effect, Schedule } from "effect";
import {
  AllCommunityModule,
  createGrid,
  ModuleRegistry,
  type ColDef,
  type GridApi,
  type GridOptions,
} from "ag-grid-community";
import { Icon } from "@iconify-icon/solid";
import { agGridCustomTheme } from "@/styles/agGridCustomTheme";
import { openInCentral } from "@/utils/openInCentral";
import { systemRuntime } from "@/config/runtime";
import { MappingService, type MappingItem } from "@/services/mapping";
import { useDynamicValues } from "@/features/network-properties-viewer/hooks/useDynamicValues";
import { alarmStore, type MonitorEntry } from "../store";
import { alarmColor, formatAlarmTime, locate, textMatcher } from "../display";

ModuleRegistry.registerModules([AllCommunityModule]);

export const OVERLOAD_MONITOR_TOOL = {
  id: "overload-monitor",
  title: "OverloadMonitor",
  iconId: "mdi:gauge",
  elementTag: "overload-monitor",
} as const;

/** Open the OverloadMonitor in the central dock: adds its tab, or focuses it if already open */
export const openOverloadMonitor = () => openInCentral(OVERLOAD_MONITOR_TOOL);

type Row = MonitorEntry & { live: number | null };

// Live value field of a measurement, as written by useDynamicValues
const liveField = (item: MappingItem) => `__dynamic_mapping__${item.kind}${item.side ? `__${item.side}` : ""}`;

const formatNumber = (value: number | null | undefined, digits = 1) =>
  value == null || Number.isNaN(value) ? "" : value.toFixed(digits);

const ratio = (row: Row) => {
  const value = row.live ?? row.value;
  return row.limit ? (Math.abs(value) / row.limit) * 100 : null;
};

const columns: ColDef<Row>[] = [
  { headerName: "Since", valueGetter: (p) => p.data?.since, valueFormatter: (p) => formatAlarmTime(p.value), width: 90 },
  { headerName: "Message", field: "label", flex: 2, minWidth: 160 },
  { headerName: "Level", field: "state", flex: 1, minWidth: 120 },
  {
    headerName: "Value",
    headerTooltip: "Live value (value at the last level change until received)",
    valueGetter: (p) => (p.data ? (p.data.live ?? p.data.value) : null),
    valueFormatter: (p) => formatNumber(p.value),
    width: 90,
    type: "rightAligned",
  },
  { headerName: "Limit", field: "limit", valueFormatter: (p) => formatNumber(p.value), width: 90, type: "rightAligned" },
  {
    headerName: "%",
    headerTooltip: "Value / limit",
    valueGetter: (p) => (p.data ? ratio(p.data) : null),
    valueFormatter: (p) => formatNumber(p.value, 0),
    width: 70,
    type: "rightAligned",
  },
  { headerName: "Last change", field: "time", valueFormatter: (p) => formatAlarmTime(p.value), width: 100 },
];

/**
 * OverloadMonitor: the measurement thresholds currently crossed, whatever the acknowledgement of their alarms, with the live value of the measurement.
 */
export function OverloadMonitor() {
  let gridContainer!: HTMLDivElement;
  const [api, setApi] = createSignal<GridApi<Row>>();
  const [text, setText] = createSignal("");
  const [mappingItems, setMappingItems] = createSignal<MappingItem[]>([]);
  // Live values by equipment id and field (see useDynamicValues)
  const [live, setLive] = createSignal<Record<string, Record<string, number | null>>>({});

  onMount(() => {
    const program = Effect.repeat(
      Effect.gen(function* () {
        const state = yield* (yield* MappingService).getState;
        if (!state.isLoading) setMappingItems(state.data);
      }),
      Schedule.spaced("1 second"),
    );
    const cancel = systemRuntime.runCallback(program);
    onCleanup(() => cancel());
  });

  const mappingById = createMemo(() => new Map(mappingItems().map((item) => [item.id, item])));
  // Mapping entries of the measurements in the monitor
  const monitoredItems = createMemo(() =>
    alarmStore.monitor().flatMap((entry) => mappingById().get(entry.id) ?? []),
  );

  const { start, stop } = useDynamicValues(
    monitoredItems,
    () => new Set(monitoredItems().map((item) => item.equipmentId)),
    (updates) =>
      setLive((prev) => {
        const next = { ...prev };
        for (const [equipmentId, fields] of Object.entries(updates)) {
          next[equipmentId] = { ...next[equipmentId], ...fields };
        }
        return next;
      }),
  );

  // Subscribe to the topics of the monitored measurements, again when they change (useDynamicValues reads the measurement ids at start)
  const monitoredIds = createMemo(() => monitoredItems().map((item) => item.id).sort().join("\n"));
  createEffect(() => {
    if (monitoredIds() === "") {
      stop();
      return;
    }
    const topics = [...new Set(monitoredItems().map((item) => item.topic))];
    start(topics, [], alarmStore.mode());
  });

  const rows = createMemo((): Row[] => {
    const match = textMatcher(text());
    const values = live();
    return alarmStore
      .monitor()
      .filter((entry) => match(entry.label) || match(entry.state))
      .map((entry) => {
        const item = mappingById().get(entry.id);
        return { ...entry, live: item ? (values[item.equipmentId]?.[liveField(item)] ?? null) : null };
      });
  });

  onMount(() => {
    const options: GridOptions<Row> = {
      theme: agGridCustomTheme,
      columnDefs: columns,
      rowData: [],
      getRowId: (p) => p.data.id,
      getRowStyle: (p) => ({ color: alarmColor(p.data?.color) }),
      suppressCellFocus: true,
      tooltipShowDelay: 300,
      defaultColDef: { resizable: true, sortable: true },
      overlayNoRowsTemplate:
        '<span class="opacity-70 text-[11px] font-bold uppercase tracking-wider font-sans">No threshold crossed</span>',
      onCellDoubleClicked: (e) => e.data && void locate(e.data),
    };
    const gridApi = createGrid(gridContainer, options);
    setApi(gridApi);
    onCleanup(() => gridApi.destroy());
  });

  createEffect(() => {
    const gridApi = api();
    const data = rows();
    if (gridApi && !gridApi.isDestroyed()) gridApi.setGridOption("rowData", data);
  });

  const inputClass =
    "px-2 py-0.5 text-xs bg-[var(--pre-bg)] text-[var(--fg)] border border-[var(--border)] focus:border-[var(--links)] focus:outline-none rounded-sm";

  return (
    <div class="flex flex-col h-full w-full bg-[var(--bg)] font-sans">
      <div class="px-3 py-1.5 flex items-center gap-2 border-b border-[var(--border)] shrink-0 bg-[var(--sidebar-bg)]">
        <span
          class="size-2 rounded-full shrink-0"
          title={alarmStore.connected() ? `Connected (${alarmStore.mode()})` : "Not connected"}
          style={{ background: alarmStore.connected() ? "#22c55e" : "#9ca3af" }}
        />
        <span class="text-xs font-mono text-[var(--sidebar-fg)]">{alarmStore.monitor().length} crossed</span>
        <input class={`${inputClass} w-40`} placeholder="Filter" value={text()} onInput={(e) => setText(e.currentTarget.value)} />
        <span class="text-[11px] text-[var(--sidebar-fg)] opacity-70">Double click: locate</span>
      </div>
      <div class="flex-1 overflow-hidden relative z-0 bg-[var(--pre-bg)]">
        <div ref={gridContainer} class="h-full w-full font-mono text-xs" />
      </div>
    </div>
  );
}

/** Header badge: number of thresholds crossed. Opens the OverloadMonitor. */
export const OverloadMonitorBadge = () => {
  const count = () => alarmStore.monitor().length;
  return (
    <button
      class="flex items-center gap-1 h-full px-1 rounded hover:bg-[var(--theme-hover)] cursor-pointer"
      title={`OverloadMonitor: ${count()} threshold(s) crossed`}
      onClick={openOverloadMonitor}
    >
      <Icon icon={OVERLOAD_MONITOR_TOOL.iconId} />
      <Show when={count() > 0} fallback={<span class="opacity-60">0</span>}>
        <span class="font-bold">{count()}</span>
      </Show>
    </button>
  );
};
