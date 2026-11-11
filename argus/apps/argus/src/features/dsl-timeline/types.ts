/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export type DslEventKind = "action" | "ramp" | "conditional" | "function_call";
export type DslEventStatus = "ready" | "ongoing" | "completed" | "interrupted";

// Output of DSLEngine::listEvents() (Orchestrator/DSL/DSLEngine.cpp), from GET /queue/list.
export type DslEvent = {
  id: number;
  status: DslEventStatus;
  tag: string | null;
  source: string;
  describe: string;
  kind: DslEventKind;
  execution_time?: number;
  interval_start?: number;
  interval_end?: number;
};

export type DslStatus = {
  status: string;
  current_time: number;
  simulation_name: string;
  event_counts: {
    ready: number;
    ongoing: number;
    completed: number;
    interrupted: number;
  };
};

export type EventType = "at" | "when" | "during";

export interface TimelineEvent extends Partial<Omit<DslEvent, "id">> {
  id: string;
  type: EventType;
  trigger?: string | number;
  from?: string | number;
  to?: string | number;
  action: string;
}

export interface LaidEvent extends TimelineEvent {
  t1: number;
  t2: number;
  xPx: number;
  wPx: number;
  track: number;
}

export const EVENT_ACCENTS: Record<
  EventType,
  { bg: string; text: string; mark: string; border: string }
> = {
  at: {
    bg: "rgba(245, 158, 11, 0.15)",
    text: "#f59e0b",
    mark: "#f59e0b",
    border: "rgba(245, 158, 11, 0.4)",
  },
  when: {
    bg: "rgba(16, 185, 129, 0.15)",
    text: "#10b981",
    mark: "#10b981",
    border: "rgba(16, 185, 129, 0.4)",
  },
  during: {
    bg: "rgba(239, 68, 68, 0.15)",
    text: "#ef4444",
    mark: "#ef4444",
    border: "rgba(239, 68, 68, 0.4)",
  },
};

export const PAD_L = 20;
export const RULER_H = 32;
export const TRACK_H = 34;
export const DEFAULT_SPACING_PPS = 5;
