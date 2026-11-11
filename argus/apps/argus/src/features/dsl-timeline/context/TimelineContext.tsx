/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createContext,
  useContext,
  createSignal,
  createMemo,
  onMount,
  onCleanup,
  ParentComponent,
  createEffect,
} from "solid-js";
import { Effect, Exit, Stream, Schedule } from "effect";
import { TimeClient } from "@/services/time/service";
import { DslClient } from "@/services/dsl/service";
import { describeDslError, type DslError } from "@/services/dsl/error";
import { systemRuntime } from "@/config/runtime";
import {
  DEFAULT_SPACING_PPS,
  type TimelineEvent,
  type DslStatus,
  type EventType,
  type DslEvent,
} from "../types";

export type ContextMenuState =
  | { type: "event"; event: TimelineEvent; x: number; y: number }
  | { type: "background"; time: number; x: number; y: number }
  | null;

interface TimelineContextValue {
  currentTime: () => number;
  spacing: () => number;
  setSpacing: (s: number) => void;
  status: () => DslStatus | null;
  statusError: () => Error | null;
  events: () => TimelineEvent[];
  whenEvents: () => TimelineEvent[];
  selectedId: () => string | null;
  setSelectedId: (id: string | null) => void;
  contextMenu: () => ContextMenuState;
  setContextMenu: (state: ContextMenuState) => void;
  deleteEvent: (id: string) => void;
  addEvent: (dsl: string) => void;
  /** What the engine said about the last rejected add/delete, until it is dismissed or another one is attempted. */
  mutationError: () => string | null;
  dismissMutationError: () => void;
  /** Replaces a Ready event's DSL text (PUT /queue/{id}). Resolves to the new event's id. */
  editEvent: (id: string, newDslText: string) => Promise<string>;
  dslInput: () => string;
  setDslInput: (val: string) => void;
  leftDrawerOpen: () => boolean;
  setLeftDrawerOpen: (open: boolean) => void;
}

const TimelineContext = createContext<TimelineContextValue>();

const toTimelineEvent = (e: DslEvent): TimelineEvent => {
  let type: EventType = "at";
  let trigger, from, to;

  // A ramp always reports interval_start/interval_end. A function_call reports them only when its children
  // span a range, and execution_time when they all land on the same instant.
  if (e.interval_start !== undefined && e.interval_end !== undefined) {
    type = "during";
    from = e.interval_start;
    to = e.interval_end;
  } else if (e.kind === "conditional") {
    type = "when";
  } else {
    type = "at";
    trigger = e.execution_time;
  }

  return {
    ...e,
    id: String(e.id),
    type,
    trigger,
    from,
    to,
    action: e.describe || e.source || "Event",
  };
};

const getInitialSpacing = (): number => {
  try {
    const stored = localStorage.getItem("timeline-spacing");
    if (stored !== null) {
      const parsed = parseFloat(stored);
      if (!isNaN(parsed) && parsed > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn("Cannot read timeline spacing from localStorage:", e);
  }
  return DEFAULT_SPACING_PPS;
};

export const TimelineProvider: ParentComponent = (props) => {
  const [currentTime, setCurrentTime] = createSignal(0);
  const [dslInput, setDslInput] = createSignal("");
  const [leftDrawerOpen, setLeftDrawerOpen] = createSignal(false);

  const [spacing, setSpacing] = createSignal(getInitialSpacing());

  createEffect(() => {
    try {
      localStorage.setItem("timeline-spacing", String(spacing()));
    } catch (e) {
      console.warn("Impossible de sauvegarder le zoom:", e);
    }
  });

  const [status, setStatus] = createSignal<DslStatus | null>(null);
  const [statusError, setStatusError] = createSignal<Error | null>(null);
  const [mutationError, setMutationError] = createSignal<string | null>(null);
  const [remoteEvents, setRemoteEvents] = createSignal<TimelineEvent[]>([]);
  const [selectedId, setSelectedId] = createSignal<string | null>(null);
  const [contextMenu, setContextMenu] = createSignal<ContextMenuState>(null);

  // Events of the previous poll, by id, with the fields they were built from. An unchanged event keeps its object,
  // so that the timeline does not re-create its clip at each poll (a replayed scenario can have ~30k events).
  let eventCache = new Map<string, { key: string; event: TimelineEvent }>();

  const updateEvents = (evs: DslEvent[]) => {
    const previous = remoteEvents();
    const nextCache = new Map<string, { key: string; event: TimelineEvent }>();
    let changed = evs.length !== previous.length;
    const next = evs.map((e, i) => {
      const id = String(e.id);
      const key = `${e.status}|${e.tag}|${e.source}|${e.describe}|${e.kind}|${e.execution_time}|${e.interval_start}|${e.interval_end}`;
      const cached = eventCache.get(id);
      const event = cached && cached.key === key ? cached.event : toTimelineEvent(e);
      nextCache.set(id, { key, event });
      if (event !== previous[i]) changed = true;
      return event;
    });
    eventCache = nextCache;
    if (changed) setRemoteEvents(next);
  };

  /** One read of the engine's status and queue. Shared by the poller and by refreshNow(). */
  const fetchState = Effect.gen(function* () {
    const dsl = yield* DslClient;
    const statusData = yield* dsl.get<DslStatus>("/status");
    setStatus(statusData);
    setStatusError(null);

    const evs = yield* dsl.get<DslEvent[]>("/queue/list");
    updateEvents(evs);
  });

  /**
   * Re-reads the queue without waiting for the next poll, so the outcome of a mutation shows at once.
   * The timeline shows what the engine reports rather than a local guess, because a delete does not always
   * remove: DELETE drops a Ready event, but interrupts and keeps an Ongoing one, and refuses a finished one.
   */
  const refreshNow = () => {
    systemRuntime.runCallback(fetchState.pipe(Effect.catchAll(() => Effect.void)));
  };

  /** Runs a mutation, reports a rejection in mutationError, and re-reads the queue either way. */
  const runMutation = (task: Effect.Effect<unknown, DslError, DslClient>) => {
    setMutationError(null);
    systemRuntime.runCallback(task, {
      onExit: (exit) => {
        if (Exit.isFailure(exit)) {
          setMutationError(
            exit.cause._tag === "Fail"
              ? describeDslError(exit.cause.error)
              : "The command could not be sent to the DSL engine.",
          );
        }
        refreshNow();
      },
    });
  };

  onMount(() => {
    const timeSub = Effect.gen(function* () {
      const timeClient = yield* TimeClient;
      yield* timeClient.time.pipe(
        Stream.runForEach((newTime) =>
          Effect.sync(() => setCurrentTime(newTime.current_time)),
        ),
      );
    }).pipe(
      Effect.retry(Schedule.spaced("2 seconds")),
      Effect.repeat(Schedule.spaced("2 seconds")),
    );

    const dslPolling = fetchState.pipe(
      Effect.catchAll((err) => {
        setStatusError(err as Error);
        return Effect.succeed(null);
      }),
      Effect.repeat(Schedule.spaced("1 seconds")),
    );

    const cancelTime = systemRuntime.runCallback(timeSub);
    const cancelPolling = systemRuntime.runCallback(dslPolling);

    onCleanup(() => {
      cancelTime();
      cancelPolling();
    });
  });

  const deleteEvent = (id: string) => {
    runMutation(
      Effect.gen(function* () {
        const dsl = yield* DslClient;
        yield* dsl.delete(`/queue/${id}`);
      }),
    );
  };

  const addEvent = (dslText: string) => {
    runMutation(
      Effect.gen(function* () {
        const dsl = yield* DslClient;
        yield* dsl.post("/trainer/dsl_command", dslText, "argus:dsl-timeline");  // TODO: put user name as source instead
      }),
    );
  };

  const editEvent = (id: string, newDslText: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const task = Effect.gen(function* () {
        const dsl = yield* DslClient;
        return yield* dsl.put<{ id: number }>(
          `/queue/${id}`,
          newDslText,
          "argus:dsl-timeline",  // TODO: put user name as source instead
        );
      });

      systemRuntime.runCallback(task, {
        onExit: (exit) => {
          if (Exit.isSuccess(exit)) {
            resolve(String(exit.value.id));
          } else if (exit.cause._tag === "Fail") {
            reject(new Error(describeDslError(exit.cause.error)));
          } else {
            reject(new Error("Unexpected failure"));
          }
        },
      });
    });
  };

  const allEvents = createMemo(() => remoteEvents());
  const events = createMemo(() => allEvents().filter((e) => e.type !== "when"));
  const whenEvents = createMemo(() => allEvents().filter((e) => e.type === "when"));

  return (
    <TimelineContext.Provider
      value={{
        currentTime,
        spacing,
        setSpacing,
        status,
        statusError,
        events,
        whenEvents,
        selectedId,
        setSelectedId,
        contextMenu,
        setContextMenu,
        deleteEvent,
        addEvent,
        mutationError,
        dismissMutationError: () => setMutationError(null),
        editEvent,
        dslInput,
        setDslInput,

        leftDrawerOpen,
        setLeftDrawerOpen,
      }}
    >
      {props.children}
    </TimelineContext.Provider>
  );
};

export function useTimeline() {
  const context = useContext(TimelineContext);
  if (!context)
    throw new Error("useTimeline must be used within a TimelineProvider");
  return context;
}
