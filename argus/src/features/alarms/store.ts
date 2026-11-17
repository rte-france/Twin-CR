/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createMemo, createRoot, createSignal, createEffect, on } from "solid-js";
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

type AlarmMessage =
  | { type: "snapshot"; alarms: Alarm[]; events: AlarmEvent[] }
  | { type: "alarm"; alarm: Alarm }
  | { type: "alarm_removed"; uid: number }
  | { type: "event"; event: AlarmEvent }
  | { type: "keepalive" };

/** A persistent alarm acknowledged and ended, that the operator has to clear */
export const isToClear = (a: Alarm) => a.mode === "persistent" && a.acked && a.ended;

// Changes are applied to plain collections and published to the views at most every FLUSH_MS (bursts of alarms)
const FLUSH_MS = 200;
// Events kept, as in the backend journal (AlarmService.MAX_EVENTS)
const MAX_EVENTS = 10_000;

const store = createRoot(() => {
  const [mode] = useAppMode();
  const [version, setVersion] = createSignal(0);
  const [connected, setConnected] = createSignal(false);
  const alarmsByUid = new Map<number, Alarm>();
  let events: AlarmEvent[] = [];  // Oldest first
  let flushTimer: ReturnType<typeof setTimeout> | undefined;
  let cancelStream: (() => void) | undefined;

  const scheduleFlush = () => {
    if (flushTimer !== undefined) return;
    flushTimer = setTimeout(() => {
      flushTimer = undefined;
      setVersion((v) => v + 1);
    }, FLUSH_MS);
  };

  const apply = (message: AlarmMessage) => {
    switch (message.type) {
      case "snapshot":
        alarmsByUid.clear();
        for (const a of message.alarms) alarmsByUid.set(a.uid, a);
        events = [...message.events];
        break;
      case "alarm":
        alarmsByUid.set(message.alarm.uid, message.alarm);
        break;
      case "alarm_removed":
        alarmsByUid.delete(message.uid);
        break;
      case "event":
        events.push(message.event);
        if (events.length > MAX_EVENTS) events.splice(0, events.length - MAX_EVENTS);
        break;
      default:
        return;
    }
    scheduleFlush();
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
    events = [];
    setVersion((v) => v + 1);

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
    version();
    return [...alarmsByUid.values()].sort((a, b) => b.time - a.time || b.uid - a.uid);
  });
  const eventList = createMemo(() => {
    version();
    return [...events].reverse();
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
    acknowledge: (uids: number[]) => uids.length > 0 && post("/alarms/acknowledge", { uids }),
    clear: (uids: number[]) => uids.length > 0 && post("/alarms/clear", { uids }),
    comment: (uid: number, comment: string | null) => post("/alarms/comment", { uid, comment }),
  };
});

export const alarmStore = store;
