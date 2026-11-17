/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, createMemo, createSignal, For, onCleanup, onMount, Show } from "solid-js";
import {
  AllCommunityModule,
  createGrid,
  ModuleRegistry,
  type ColDef,
  type GridApi,
  type GridOptions,
} from "ag-grid-community";
import { agGridCustomTheme } from "@/styles/agGridCustomTheme";
import { alarmStore, isToClear, type Alarm, type AlarmEvent } from "../store";
import { alarmColor, canLocate, formatAlarmTime, locate, parseTime, textMatcher } from "../display";
import { alarmsMuted, setAlarmsMuted } from "../sound";

ModuleRegistry.registerModules([AllCommunityModule]);

type Variant = "alarms" | "events";
type Row = Alarm | AlarmEvent;

const rowKey = (variant: Variant, row: Row) =>
  variant === "alarms" ? String((row as Alarm).uid) : String((row as AlarmEvent).seq);

const timeColumn: ColDef = {
  headerName: "Time",
  valueGetter: (p) => p.data?.time,
  valueFormatter: (p) => formatAlarmTime(p.value),
  width: 90,
};

const messageColumns: ColDef[] = [
  { headerName: "Message", field: "label", flex: 2, minWidth: 160 },
  { headerName: "State", field: "state", flex: 1, minWidth: 100 },
];

// Status columns: U (unacknowledged), P (persistent), D (to clear), C (comment)
const alarmColumns: ColDef[] = [
  timeColumn,
  {
    headerName: "U",
    headerTooltip: "Not acknowledged",
    width: 42,
    valueGetter: (p) => (p.data?.acked ? "" : "●"),
  },
  {
    headerName: "P",
    headerTooltip: "Persistent: acknowledge, then clear once ended",
    width: 42,
    valueGetter: (p) => (p.data?.mode === "persistent" ? "◆" : ""),
  },
  {
    headerName: "D",
    headerTooltip: "To clear (✕), or waiting for the end of the alarm (⏳)",
    width: 42,
    valueGetter: (p) => {
      const a = p.data as Alarm | undefined;
      if (!a || a.mode !== "persistent" || !a.acked) return "";
      return a.ended ? "✕" : "⏳";
    },
  },
  {
    headerName: "C",
    headerTooltip: "Comment",
    width: 42,
    valueGetter: (p) => (p.data?.comment ? "✎" : ""),
    tooltipValueGetter: (p) => p.data?.comment ?? undefined,
  },
  ...messageColumns,
];

const eventColumns: ColDef[] = [timeColumn, ...messageColumns];

export function AlarmWindow(props: { variant: Variant }) {
  let gridContainer!: HTMLDivElement;
  const [api, setApi] = createSignal<GridApi<Row>>();
  const [frozen, setFrozen] = createSignal(false);
  const [autoScroll, setAutoScroll] = createSignal(true);
  const [frozenRows, setFrozenRows] = createSignal<Row[]>([]);
  const [text, setText] = createSignal("");
  const [kind, setKind] = createSignal("");
  const [from, setFrom] = createSignal("");
  const [to, setTo] = createSignal("");
  const [selected, setSelected] = createSignal<Alarm[]>([]);
  const [menu, setMenu] = createSignal<{ x: number; y: number; alarm: Alarm } | null>(null);
  const [commenting, setCommenting] = createSignal<Alarm | null>(null);
  const [commentText, setCommentText] = createSignal("");

  const isAlarms = () => props.variant === "alarms";
  const liveRows = (): Row[] => (isAlarms() ? alarmStore.alarms() : alarmStore.events());
  // Frozen: no new rows, but the rows shown keep their latest state, and disappear once acknowledged/cleared
  const sourceRows = (): Row[] => {
    if (!frozen()) return liveRows();
    const live = new Map(liveRows().map((r) => [rowKey(props.variant, r), r]));
    return frozenRows().flatMap((r) => live.get(rowKey(props.variant, r)) ?? []);
  };

  const filtered = () => text() !== "" || kind() !== "" || from() !== "" || to() !== "";
  const rows = createMemo(() => {
    const match = textMatcher(text());
    const k = kind();
    const min = parseTime(from());
    const max = parseTime(to());
    return sourceRows().filter(
      (r) =>
        (k === "" || r.kind === k) &&
        (min === null || r.time >= min) &&
        (max === null || r.time <= max) &&
        (match(r.label) || match(r.state)),
    );
  });
  const kinds = createMemo(() => [...new Set(liveRows().map((r) => r.kind))].sort());

  const counters = createMemo(() => {
    const alarms = alarmStore.alarms();
    return {
      total: alarms.length,
      unacked: alarms.filter((a) => !a.acked).length,
      persistent: alarms.filter((a) => a.mode === "persistent").length,
      toClear: alarms.filter(isToClear).length,
    };
  });

  const freeze = (value: boolean) => {
    if (value && !frozen()) setFrozenRows(liveRows());
    setFrozen(value);
  };

  const acknowledge = (alarms: Alarm[]) => alarmStore.acknowledge(alarms.filter((a) => !a.acked).map((a) => a.uid));
  const clear = (alarms: Alarm[]) => alarmStore.clear(alarms.filter(isToClear).map((a) => a.uid));
  const visibleAlarms = () => (isAlarms() ? (rows() as Alarm[]) : []);

  const openComment = (alarm: Alarm) => {
    setMenu(null);
    setCommentText(alarm.comment ?? "");
    setCommenting(alarm);
  };

  const saveComment = (value: string | null) => {
    const alarm = commenting();
    if (alarm) void alarmStore.comment(alarm.uid, value);
    setCommenting(null);
  };

  onMount(() => {
    const options: GridOptions<Row> = {
      theme: agGridCustomTheme,
      columnDefs: isAlarms() ? alarmColumns : eventColumns,
      rowData: [],
      getRowId: (p) => rowKey(props.variant, p.data),
      getRowStyle: (p) => ({
        color: alarmColor(p.data?.color),
        "font-weight": isAlarms() && p.data && !(p.data as Alarm).acked ? "bold" : "normal",
      }),
      rowSelection: isAlarms()
        ? { mode: "multiRow", checkboxes: false, headerCheckbox: false, enableClickSelection: true }
        : undefined,
      suppressCellFocus: true,
      tooltipShowDelay: 300,
      defaultColDef: { resizable: true, sortable: false },
      overlayNoRowsTemplate: `<span class="opacity-70 text-[11px] font-bold uppercase tracking-wider font-sans">No ${props.variant}</span>`,
      onSelectionChanged: (e) => setSelected(e.api.getSelectedRows() as Alarm[]),
      // Clicking an alarm freezes the window, so that it does not move while acting on it
      onRowClicked: () => freeze(true),
      onCellContextMenu: (e) => {
        if (!isAlarms() || !e.data) return;
        const event = e.event as MouseEvent;
        event.preventDefault();
        if (!e.node.isSelected()) e.node.setSelected(true, true);
        freeze(true);
        setMenu({ x: event.clientX, y: event.clientY, alarm: e.data as Alarm });
      },
      onCellDoubleClicked: (e) => e.data && void locate(e.data),
      preventDefaultOnContextMenu: true,
    };
    const gridApi = createGrid(gridContainer, options);
    setApi(gridApi);
    onCleanup(() => gridApi.destroy());

    const closeMenu = () => setMenu(null);
    window.addEventListener("click", closeMenu);
    onCleanup(() => window.removeEventListener("click", closeMenu));
  });

  createEffect(() => {
    const gridApi = api();
    const data = rows();
    if (!gridApi || gridApi.isDestroyed()) return;
    gridApi.setGridOption("rowData", data);
    if (autoScroll() && !frozen() && data.length > 0) gridApi.ensureIndexVisible(0, "top");
  });

  // Alt+A: acknowledge the selection, F4: acknowledge the visible alarms
  const onKeyDown = (e: KeyboardEvent) => {
    if (!isAlarms() || commenting()) return;
    if (e.altKey && e.key.toLowerCase() === "a") {
      e.preventDefault();
      void acknowledge(selected());
    } else if (e.key === "F4") {
      e.preventDefault();
      void acknowledge(visibleAlarms());
    }
  };

  const inputClass =
    "px-2 py-0.5 text-xs bg-[var(--pre-bg)] text-[var(--fg)] border border-[var(--border)] focus:border-[var(--links)] focus:outline-none rounded-sm";
  const buttonClass =
    "px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider rounded border border-[var(--border)] hover:bg-[var(--theme-hover)] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer";
  const menuItemClass = "block w-full text-left px-3 py-1 text-xs hover:bg-[var(--theme-hover)] disabled:opacity-40 disabled:cursor-not-allowed";

  return (
    <div tabIndex={0} onKeyDown={onKeyDown} class="flex flex-col h-full w-full bg-[var(--bg)] font-sans relative outline-none">
      {/* Banner: highlighted when filtered, hatched when frozen */}
      <div
        class="px-3 py-1.5 flex flex-wrap items-center gap-2 border-b border-[var(--border)] shrink-0 bg-[var(--sidebar-bg)]"
        style={{
          "box-shadow": filtered() ? "inset 0 -2px 0 #eab308" : undefined,
          "background-image": frozen()
            ? "repeating-linear-gradient(45deg, transparent 0 6px, rgba(127,127,127,0.15) 6px 12px)"
            : undefined,
        }}
      >
        <span
          class="size-2 rounded-full shrink-0"
          title={alarmStore.connected() ? `Connected (${alarmStore.mode()})` : "Not connected"}
          style={{ background: alarmStore.connected() ? "#22c55e" : "#9ca3af" }}
        />
        <Show
          when={isAlarms()}
          fallback={<span class="text-xs font-mono text-[var(--sidebar-fg)]">{alarmStore.events().length} events</span>}
        >
          <span
            class="text-xs font-mono text-[var(--sidebar-fg)]"
            title="Total / not acknowledged / persistent / to clear"
          >
            {counters().total}/{counters().unacked}/{counters().persistent}/{counters().toClear}
          </span>
        </Show>
        <input class={`${inputClass} w-40`} placeholder="Filter (e.g. *BREAKER*)" value={text()} onInput={(e) => setText(e.currentTarget.value)} />
        <select class={inputClass} value={kind()} onChange={(e) => setKind(e.currentTarget.value)}>
          <option value="">All types</option>
          <For each={kinds()}>{(k) => <option value={k}>{k}</option>}</For>
        </select>
        <input class={`${inputClass} w-20`} placeholder="From" title="From time (HH:MM:SS)" value={from()} onInput={(e) => setFrom(e.currentTarget.value)} />
        <input class={`${inputClass} w-20`} placeholder="To" title="To time (HH:MM:SS)" value={to()} onInput={(e) => setTo(e.currentTarget.value)} />
        <Show when={filtered()}>
          <button class={buttonClass} onClick={() => { setText(""); setKind(""); setFrom(""); setTo(""); }}>Reset</button>
        </Show>
        <div class="flex-1" />
        <Show when={isAlarms()}>
          <button class={buttonClass} disabled={selected().every((a) => a.acked)} onClick={() => acknowledge(selected())} title="Acknowledge the selection (Alt+A)">
            Ack
          </button>
          <button class={buttonClass} onClick={() => acknowledge(visibleAlarms())} title="Acknowledge the visible alarms (F4)">
            Ack visible
          </button>
          <button class={buttonClass} disabled={!selected().some(isToClear)} onClick={() => clear(selected())} title="Clear the selection (acknowledged and ended persistent alarms)">
            Clear
          </button>
          <button class={buttonClass} onClick={() => setAlarmsMuted(!alarmsMuted())} title="Sound">
            {alarmsMuted() ? "🔇" : "🔊"}
          </button>
        </Show>
        <label class="flex items-center gap-1 text-xs text-[var(--sidebar-fg)]">
          <input type="checkbox" checked={frozen()} onChange={(e) => freeze(e.currentTarget.checked)} /> Frozen
        </label>
        <label class="flex items-center gap-1 text-xs text-[var(--sidebar-fg)]">
          <input type="checkbox" checked={autoScroll()} onChange={(e) => setAutoScroll(e.currentTarget.checked)} /> AutoScroll
        </label>
      </div>

      <div class="flex-1 overflow-hidden relative z-0 bg-[var(--pre-bg)]">
        <div ref={gridContainer} class="h-full w-full font-mono text-xs" />
      </div>

      <Show when={menu()}>
        {(m) => (
          <div
            class="fixed z-50 min-w-40 py-1 rounded border border-[var(--popover-border)] bg-[var(--popover-bg)] shadow-lg"
            style={{ left: `${m().x}px`, top: `${m().y}px` }}
            onClick={(e) => e.stopPropagation()}
          >
            <button class={menuItemClass} disabled={selected().every((a) => a.acked)} onClick={() => { void acknowledge(selected()); setMenu(null); }}>
              Acknowledge
            </button>
            <button class={menuItemClass} disabled={!selected().some(isToClear)} onClick={() => { void clear(selected()); setMenu(null); }}>
              Clear
            </button>
            <button class={menuItemClass} onClick={() => openComment(m().alarm)}>
              {m().alarm.comment ? "Edit comment" : "Comment"}
            </button>
            <button class={menuItemClass} disabled={!canLocate(m().alarm)} onClick={() => { void locate(m().alarm); setMenu(null); }}>
              Locate
            </button>
          </div>
        )}
      </Show>

      <Show when={commenting()}>
        {(alarm) => (
          <div class="absolute inset-0 z-40 flex items-center justify-center bg-black/30">
            <div class="w-96 p-3 rounded border border-[var(--popover-border)] bg-[var(--popover-bg)] shadow-lg flex flex-col gap-2">
              <span class="text-xs font-bold">{alarm().label} {alarm().state}</span>
              <textarea
                class={`${inputClass} h-24 resize-none`}
                value={commentText()}
                onInput={(e) => setCommentText(e.currentTarget.value)}
                ref={(el) => setTimeout(() => el.focus())}
              />
              <div class="flex justify-end gap-2">
                <Show when={alarm().comment}>
                  <button class={buttonClass} onClick={() => saveComment(null)}>Delete</button>
                </Show>
                <button class={buttonClass} onClick={() => setCommenting(null)}>Cancel</button>
                <button class={buttonClass} onClick={() => saveComment(commentText())}>Save</button>
              </div>
            </div>
          </div>
        )}
      </Show>
    </div>
  );
}
