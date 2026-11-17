/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, createRoot, createSignal } from "solid-js";
import { alarmStore, type Alarm } from "./store";

/**
 * Alarm sounds, played in the main window until the alarms are acknowledged: each new alarm is announced at once,
 * then the sound of the unacknowledged alarm of highest priority is repeated every REPEAT_MS.
 * Placeholder tones synthesised with WebAudio, one pattern per sound name (grey, blue, yellow, red, violet).
 */
const REPEAT_MS = 3000;
const MUTED_KEY = "argus:alarms-muted";

// [frequency (Hz), duration (s)] per beep
const PATTERNS: Record<string, [number, number][]> = {
  grey: [[440, 0.15]],
  blue: [[660, 0.12], [660, 0.12]],
  yellow: [[880, 0.12], [880, 0.12], [880, 0.12]],
  red: [[1100, 0.1], [1100, 0.1], [1100, 0.1], [1100, 0.1]],
  violet: [[1200, 0.12], [900, 0.12], [1200, 0.12], [900, 0.12]],
};
const GAP_S = 0.08;
const VOLUME = 0.15;

const loadMuted = () => {
  try {
    return localStorage.getItem(MUTED_KEY) === "true";
  } catch {
    return false;
  }
};

const [muted, setMutedSignal] = createSignal(loadMuted());

export const alarmsMuted = muted;

export const setAlarmsMuted = (value: boolean) => {
  setMutedSignal(value);
  try {
    localStorage.setItem(MUTED_KEY, String(value));
  } catch {
    // Not persisted
  }
};

let context: AudioContext | undefined;

const audioContext = () => {
  context ??= new AudioContext();
  return context;
};

export const playAlarmSound = (sound: string) => {
  const ctx = audioContext();
  if (ctx.state === "suspended") void ctx.resume();
  let start = ctx.currentTime + 0.02;
  for (const [frequency, duration] of PATTERNS[sound] ?? PATTERNS.grey) {
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(VOLUME, start);
    gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
    oscillator.connect(gain).connect(ctx.destination);
    oscillator.start(start);
    oscillator.stop(start + duration);
    start += duration + GAP_S;
  }
};

/** Sound of the alarm of highest priority, null if none */
const highestSound = (alarms: Alarm[]) => {
  let best: Alarm | null = null;
  for (const alarm of alarms) {
    if (!best || alarm.priority > best.priority) best = alarm;
  }
  return best?.sound ?? null;
};

let started = false;

/** Start the sound loop (once, main window only) */
export const startAlarmSounds = () => {
  if (started) return;
  started = true;

  // Browsers only start audio after a user gesture
  window.addEventListener("pointerdown", () => {
    if (context?.state === "suspended") void context.resume();
  });

  createRoot(() => {
    let timer: ReturnType<typeof setInterval> | undefined;
    let loopSound: string | null = null;
    let announced = new Set<number>();  // Unacknowledged alarms already announced

    const restartLoop = (sound: string | null) => {
      if (timer !== undefined) clearInterval(timer);
      timer = undefined;
      loopSound = sound;
      if (sound) timer = setInterval(() => playAlarmSound(sound), REPEAT_MS);
    };

    createEffect(() => {
      // Unacknowledged alarms with a sound (whatever the alarm windows show, e.g. when frozen)
      const ringing = alarmStore.alarms().filter((a) => !a.acked && a.sound);
      const fresh = ringing.filter((a) => !announced.has(a.uid));
      announced = new Set(ringing.map((a) => a.uid));
      if (muted()) {
        restartLoop(null);
        return;
      }
      const sound = highestSound(ringing);
      if (fresh.length > 0) {
        // Each new alarm is announced at once, even if a sound of higher priority is already looping
        playAlarmSound(highestSound(fresh)!);
        restartLoop(sound);
      } else if (sound !== loopSound) {
        // e.g. the alarm of highest priority was acknowledged: loop the next one
        restartLoop(sound);
      }
    });
  });
};
