/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createMemo, onMount, onCleanup, Show } from "solid-js";
import { Effect, Stream, Schedule } from "effect";
import { TimeClient } from "@/services/time/service";
import { systemRuntime } from "@/config/runtime";

export const Clock = () => {
  const [time, setTime] = createSignal<number>(0);
  const [isPaused, setIsPaused] = createSignal<boolean>(true);

  const formattedTime = createMemo(() => {
    const t = time();
    const hours = Math.floor(t / 3600)
      .toString()
      .padStart(2, "0");
    const minutes = Math.floor((t % 3600) / 60)
      .toString()
      .padStart(2, "0");
    const seconds = (t % 60).toString().padStart(2, "0");
    return `${hours}:${minutes}:${seconds}`;
  });

  onMount(() => {
    let timeoutId: ReturnType<typeof setTimeout>;

    const timeSubscription = Effect.gen(function* () {
      const timeClient = yield* TimeClient;

      yield* timeClient.time.pipe(
        Stream.runForEach((newTime) =>
          Effect.sync(() => {
            const current = newTime.current_time;

            if (current > time()) {
              setIsPaused(false);
            } else {
              setIsPaused(true);
            }

            setTime(current);

            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
              setIsPaused(true);
            }, 1500);
          }),
        ),
      );
    }).pipe(
      Effect.retry(Schedule.spaced("2 seconds")),
      Effect.repeat(Schedule.spaced("2 seconds")),
    );

    const cancelSubscription = systemRuntime.runCallback(timeSubscription);

    onCleanup(() => {
      cancelSubscription();
      clearTimeout(timeoutId);
    });
  });

  return (
    <div
      class="flex items-baseline gap-1.5 tabular-nums leading-none translate-y-[1px]"
      style={{ "font-family": "var(--mono-font)" }}
    >
      <span class="text-[12px] font-semibold text-(--success-color)">
        {formattedTime()}
      </span>
      <span class="text-[10px] font-medium text-(--icons)">
        {time()}
        <span class="text-[8px] opacity-70 ml-[2px]">s</span>
      </span>
    </div>
  );
};
