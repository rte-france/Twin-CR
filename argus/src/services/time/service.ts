/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  Context,
  Effect,
  Layer,
  Schedule,
  Stream,
  SubscriptionRef,
} from "effect";
import { GmClient } from "../game-master/service";
import { TimeError } from "./error";
import { AppMode, Mode } from "../app-mode";
import { ScadaClient } from "../scada/service";

export interface SimulationTime {
  current_time: number;
}

export class TimeClient extends Context.Tag("TimeClient")<
  TimeClient,
  {
    readonly getTime: Effect.Effect<SimulationTime>;
    readonly time: Stream.Stream<SimulationTime, TimeError>;
  }
>() {}

export const TimeClientLive = Layer.scoped(
  TimeClient,
  Effect.gen(function* () {
    const appMode = yield* AppMode;
    const gm = yield* GmClient;
    const scada = yield* ScadaClient;

    const timeRef = yield* SubscriptionRef.make<SimulationTime>({
      current_time: 0,
    });

    const timeStream = Stream.fromEffect(appMode.getMode).pipe(
      Stream.flatMap((mode) => {
        if (mode === Mode.GameMaster) {
          return gm.sseStream<SimulationTime>("/time");
        } else {
          return scada.sseStream<SimulationTime>("/time");
        }
      }),
      Stream.retry(Schedule.spaced("2 seconds")),
      Stream.repeat(Schedule.spaced("2 seconds")),
    );

    yield* timeStream.pipe(
      Stream.runForEach((newTime) => SubscriptionRef.set(timeRef, newTime)),
      Effect.forkScoped,
    );

    return {
      getTime: SubscriptionRef.get(timeRef),
      time: timeStream,
    };
  }),
);
