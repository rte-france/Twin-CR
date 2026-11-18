/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { batch, createMemo, createRoot, createSignal, createEffect, on } from "solid-js";
import { Duration, Effect, Schedule, Stream } from "effect";
import { systemRuntime } from "@/config/runtime";
import { GmClient } from "@/services/game-master/service";
import { ScadaClient } from "@/services/scada/service";
import { Mode } from "@/services/app-mode";
import { useAppMode } from "@/hooks/useAppMode";

/** Alarm of the backend alarm list (see AlarmService in the argus backends) */
export interface Alarm {
  uid: number;
  id: string;
  label: string;
  time: number;
  value: number;
  state: string;
  kind: string;
  alarm: boolean;
  priority: number;
  color: string;
  sound: string | null;
  mode: "momentary" | "persistent";
  retain: boolean;
  normal: boolean;
  initial: boolean;
  acked: boolean;
  ended: boolean;
  end_time?: number;
  comment: string | null;
  equipment_id?: string;
  side?: string;
  substation_id?: string;
}

/** Entry of the event journal */
export interface AlarmEvent {
  seq: number;
  time: number;
  id: string;
  label: string;
  state: string;
  kind: string;
  alarm: boolean;
  priority: number;
  color: string;
  uid?: number;
  equipment_id?: string;
  side?: string;
  substation_id?: string;
}

/** OverloadMonitor entry: a threshold currently crossed (whatever the acknowledgements), by id */
export interface MonitorEntry {
  id: string;
  label: string;
  state: string;  // Level crossed, e.g. Limit 1 overload
  value: number;  // At the last level change
  limit?: number;  // Threshold of the level
  time: number;  // Last level change
  since: number;  // First crossing
  priority: number;
  color: string;
  equipment_id?: string;
  side?: string;
  substation_id?: string;
}

type AlarmMessage =
  | { type: "snapshot"; alarms: Alarm[]; events: AlarmEvent[]; monitor?: MonitorEntry[] }
  | { type: "alarm"; alarm: Alarm }
  | { type: "alarm_removed"; uid: number }
  | { type: "event"; event: AlarmEvent }
  | { type: "monitor"; entry: MonitorEntry }
  | { type: "monitor_removed"; id: string }
  | { type: "keepalive" };

/** A persistent alarm acknowledged and ended, that the operator has to clear */
export const isToClear = (a: Alarm) => a.mode === "persistent" && a.acked && a.ended;

// Changes are applied to plain collections and published to the views at most every FLUSH_MS (bursts of alarms)
const FLUSH_MS = 200;
// Events kept, as in the backend journal (AlarmService.MAX_EVENTS)
const MAX_EVENTS = 10_000;

const store = createRoot(() => {
  const [mode] = useAppMode();
  // One version per collection: a change only recomputes the views of its collection
  const [alarmsVersion, setAlarmsVersion] = createSignal(0);
  const [eventsVersion, setEventsVersion] = createSignal(0);
  const [monitorVersion, setMonitorVersion] = createSignal(0);
  const dirty = { alarms: false, events: false, monitor: false };
  const [connected, setConnected] = createSignal(false);
  const alarmsByUid = new Map<number, Alarm>();
  const monitorById = new Map<string, MonitorEntry>();
  let events: AlarmEvent[] = [];  // Oldest first
  let flushTimer: ReturnType<typeof setTimeout> | undefined;
  let cancelStream: (() => void) | undefined;

  const flush = () => {
    batch(() => {
      if (dirty.alarms) setAlarmsVersion((v) => v + 1);
      if (dirty.events) setEventsVersion((v) => v + 1);
      if (dirty.monitor) setMonitorVersion((v) => v + 1);
    });
    dirty.alarms = dirty.events = dirty.monitor = false;
  };

  const scheduleFlush = (...changed: (keyof typeof dirty)[]) => {
    for (const collection of changed) dirty[collection] = true;
    if (flushTimer !== undefined) return;
    flushTimer = setTimeout(() => {
      flushTimer = undefined;
      flush();
    }, FLUSH_MS);
  };

  const apply = (message: AlarmMessage) => {
    switch (message.type) {
      case "snapshot":
        alarmsByUid.clear();
        for (const a of message.alarms) alarmsByUid.set(a.uid, a);
        events = [...message.events];
        monitorById.clear();
        for (const m of message.monitor ?? []) monitorById.set(m.id, m);
        scheduleFlush("alarms", "events", "monitor");
        break;
      case "alarm":
        alarmsByUid.set(message.alarm.uid, message.alarm);
        scheduleFlush("alarms");
        break;
      case "alarm_removed":
        alarmsByUid.delete(message.uid);
        scheduleFlush("alarms");
        break;
      case "monitor":
        monitorById.set(message.entry.id, message.entry);
        scheduleFlush("monitor");
        break;
      case "monitor_removed":
        monitorById.delete(message.id);
        scheduleFlush("monitor");
        break;
      case "event":
        events.push(message.event);
        if (events.length > MAX_EVENTS) events.splice(0, events.length - MAX_EVENTS);
        scheduleFlush("events");
        break;
      default:
        return;
    }
  };

  const parse = (raw: unknown): AlarmMessage | null => {
    if (typeof raw !== "string") return raw as AlarmMessage;
    try {
      return JSON.parse(raw.replace(/^data:\s*/, ""));
    } catch {
      return null;
    }
  };

  const connect = (currentMode: Mode) => {
    cancelStream?.();
    alarmsByUid.clear();
    monitorById.clear();
    events = [];
    dirty.alarms = dirty.events = dirty.monitor = true;
    flush();

    const consume = Effect.gen(function* () {
      const stream = currentMode === Mode.Scada
        ? (yield* ScadaClient).sseStream<unknown>("/sub-alarms")
        : (yield* GmClient).sseStream<unknown>("/sub-alarms");
      yield* Stream.runForEach(stream, (raw) =>
        Effect.sync(() => {
          const message = parse(raw);
          if (!message) return;
          setConnected(true);
          apply(message);
        }),
      );
    }).pipe(Effect.ensuring(Effect.sync(() => setConnected(false))));

    // Reconnects (the snapshot sent on connection resynchronises the state)
    const resilient = consume.pipe(
      Effect.repeat(Schedule.spaced("1 second")),
      Effect.retry(Schedule.exponential("1 second").pipe(
        Schedule.modifyDelay((delay) => Duration.min(delay, Duration.seconds(30))),
        Schedule.resetAfter("1 minute"),
      )),
    );
    cancelStream = systemRuntime.runCallback(
      resilient as Effect.Effect<unknown, unknown, never>,
      { onExit: () => setConnected(false) },
    );
  };

  createEffect(on(mode, connect));

  // Newest first
  const alarms = createMemo(() => {
    alarmsVersion();
    return [...alarmsByUid.values()].sort((a, b) => b.time - a.time || b.uid - a.uid);
  });
  const eventList = createMemo(() => {
    eventsVersion();
    return [...events].reverse();
  });
  // Highest priority first, then the oldest crossing
  const monitor = createMemo(() => {
    monitorVersion();
    return [...monitorById.values()].sort((a, b) => b.priority - a.priority || a.since - b.since);
  });

  const post = (endpoint: string, body: unknown) => {
    const program = Effect.gen(function* () {
      return mode() === Mode.Scada
        ? yield* (yield* ScadaClient).post(endpoint, JSON.stringify(body))
        : yield* (yield* GmClient).post(endpoint, JSON.stringify(body));
    });
    return systemRuntime
      .runPromise(program as Effect.Effect<unknown, unknown, never>)
      .catch((e) => console.error(`Alarm action ${endpoint} failed`, e));
  };

  return {
    mode,
    connected,
    alarms,
    events: eventList,
    monitor,
    acknowledge: (uids: number[]) => uids.length > 0 && post("/alarms/acknowledge", { uids }),
    clear: (uids: number[]) => uids.length > 0 && post("/alarms/clear", { uids }),
    comment: (uid: number, comment: string | null) => post("/alarms/comment", { uid, comment }),
  };
});

export const alarmStore = store;
