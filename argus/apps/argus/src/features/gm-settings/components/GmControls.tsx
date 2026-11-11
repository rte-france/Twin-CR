/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount, onCleanup, Show } from "solid-js";
import { Tooltip } from "@kobalte/core/tooltip";
import { TbPlayerPause, TbSquare } from "solid-icons/tb";
import { FaSolidPlay } from "solid-icons/fa";
import { Effect, Stream } from "effect";

import { describeGmError, useGmControls } from "../hooks/useGmControls";
import { TimeClient } from "@/services/time/service";
import { systemRuntime } from "@/config/runtime";
import { addNotification } from "@/features/notifications/store";

const TOOLTIP_DELAY_DURATION = 500;

export const GmControls = () => {
  const { start, pause, resume, stop, loading, error } = useGmControls();

  const [isPlaying, setIsPlaying] = createSignal(false);
  const [isStarted, setIsStarted] = createSignal(false);
  const [lastTime, setLastTime] = createSignal(0);

  onMount(() => {
    const timeSyncSubscription = Effect.gen(function* () {
      const timeClient = yield* TimeClient;

      yield* timeClient.time.pipe(
        Stream.runForEach((newTime) =>
          Effect.sync(() => {
            const current = newTime.current_time;
            const previous = lastTime();

            if (current > 0 && !isStarted()) {
              setIsStarted(true);
            }

            if (current > previous && !isPlaying()) {
              setIsPlaying(true);
            }

            setLastTime(current);
          }),
        ),
      );
    });

    const cancelTimeSync = systemRuntime.runCallback(timeSyncSubscription);

    onCleanup(() => {
      cancelTimeSync();
    });
  });

  const run = async (
    command: () => Promise<boolean>,
    onAccepted: () => void,
    past: string,
    infinitive: string,
  ) => {
    if (await command()) {
      onAccepted();
      addNotification({ message: `Simulation ${past}` });
      return;
    }

    const failure = error();
    addNotification({
      message: `Could not ${infinitive} the simulation: ${
        failure ? describeGmError(failure) : "no response"
      }`,
      type: "error",
    });
  };

  const handleStart = () =>
    run(
      start,
      () => {
        setIsStarted(true);
        setIsPlaying(true);
      },
      "started",
      "start",
    );

  const handleResume = () =>
    run(resume, () => setIsPlaying(true), "resumed", "resume");

  const handlePause = () =>
    run(pause, () => setIsPlaying(false), "paused", "pause");

  const handleStop = () =>
    run(
      stop,
      () => {
        setIsStarted(false);
        setIsPlaying(false);
        setLastTime(0);
      },
      "stopped",
      "stop",
    );

  const ActionButton = (props: {
    tooltip: string;
    onClick: () => void;
    icon: any;
    colorClass: string;
    disabled?: boolean;
  }) => (
    <Tooltip openDelay={TOOLTIP_DELAY_DURATION}>
      <Tooltip.Trigger
        as="button"
        onClick={props.onClick}
        disabled={props.disabled || loading()}
        class={`flex items-center justify-center rounded p-1 transition-all outline-none focus:outline-none hover:bg-[var(--theme-hover)] active:scale-95 disabled:opacity-40 disabled:hover:bg-transparent disabled:active:scale-100 disabled:cursor-not-allowed ${props.colorClass}`}
      >
        <props.icon class="w-3.5 h-3.5" />
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content class="z-50 rounded border border-[var(--popover-border)] bg-[var(--popover-bg)] px-2 py-1 text-xs text-[var(--fg)] shadow-md animate-in fade-in-0 zoom-in-95 outline-none">
          <Tooltip.Arrow />
          <p>{props.tooltip}</p>
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip>
  );

  return (
    <div class="flex items-center gap-1.5 h-full">
      <Show
        when={isStarted()}
        fallback={
          <ActionButton
            tooltip="Start"
            onClick={handleStart}
            icon={FaSolidPlay}
            colorClass="text-[var(--toast-border-success)]"
          />
        }
      >
        <Show
          when={isPlaying()}
          fallback={
            <ActionButton
              tooltip="Resume"
              onClick={handleResume}
              icon={FaSolidPlay}
              colorClass="text-[var(--toast-border-success)]"
            />
          }
        >
          <ActionButton
            tooltip="Pause"
            onClick={handlePause}
            icon={TbPlayerPause}
            colorClass="text-[var(--toast-border-success)]"
          />
        </Show>
      </Show>

      <ActionButton
        tooltip="Stop"
        onClick={handleStop}
        icon={TbSquare}
        colorClass="text-[var(--toast-border-error)]"
        disabled={!isStarted()}
      />
    </div>
  );
};
