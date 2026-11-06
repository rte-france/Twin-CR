/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { Effect, Stream, Schedule } from "effect";
import { systemRuntime } from "@/config/runtime";
import { GmClient } from "@/services/game-master/service";
import { TimeClient } from "@/services/time";

export interface BaseEvent {
  time: number;
}

export interface LogServiceConfig<T> {
  historyEndpoint: string;
  sseEndpoint: string;
  getKey: (event: T) => string;
}

export function createLogService<T extends BaseEvent>(
  config: LogServiceConfig<T>,
) {
  const [events, setEvents] = createSignal<T[]>([]);
  let cancelStream: (() => void) | null = null;

  return {
    get events() {
      return events();
    },

    clearLogs: () => setEvents([]),

    loadHistory: async (min: number = 0) => {
      await systemRuntime
        .runPromise(
          Effect.gen(function* () {
            const client = yield* GmClient;
            const timeClient = yield* TimeClient;
            const simTime = yield* timeClient.getTime;

            const historyData = yield* client.get<T[]>(
              `${config.historyEndpoint}?min=${min}&max=${simTime.current_time}`,
            );

            const eventsMap = new Map(
              historyData.map((item) => [config.getKey(item), item]),
            );

            setEvents(Array.from(eventsMap.values()));
          }),
        )
        .catch(() => {});
    },

    start: () => {
      if (cancelStream) return;

      const consumeStream = Effect.gen(function* () {
        const client = yield* GmClient;
        const stream = client.sseStream<any>(config.sseEndpoint);

        yield* Stream.runForEach(stream, (rawData) =>
          Effect.sync(() => {
            let parsedData: T;
            if (typeof rawData === "string") {
              try {
                const cleanString = rawData.replace(/^data:\s*/, "");
                parsedData = JSON.parse(cleanString);
              } catch (e) {
                return;
              }
            } else {
              parsedData = rawData;
            }

            setEvents((prev) => {
              const newKey = config.getKey(parsedData);
              if (prev.some((p) => config.getKey(p) === newKey)) {
                return prev;
              }
              return [...prev, parsedData];
            });
          }),
        );
      });

      const resilientStream = consumeStream.pipe(
        Effect.repeat(Schedule.spaced("1 second")),
        Effect.retry(
          Schedule.exponential("1 second").pipe(Schedule.upTo("30 seconds")),
        ),
      );

      cancelStream = systemRuntime.runCallback(resilientStream, {
        onExit: () => {
          cancelStream = null;
        },
      });
    },

    stop: () => {
      if (cancelStream) {
        cancelStream();
        cancelStream = null;
      }
    },
  };
}

export type LogService<T extends BaseEvent> = ReturnType<
  typeof createLogService<T>
>;
