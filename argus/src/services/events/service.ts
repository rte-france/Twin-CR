/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer } from "effect";
import { EVENTS } from "@/config/events";
import { registerEvents } from "./registry";

export interface EventRegistryService {
  readonly emit: <T = void>(
    type: string,
    detail?: T,
    target?: EventTarget,
  ) => Effect.Effect<void>;
}

export class EventRegistry extends Context.Tag("EventRegistry")<
  EventRegistry,
  EventRegistryService
>() {}

export const EventRegistryLive = Layer.scoped(
  EventRegistry,
  Effect.gen(function* () {
    yield* Effect.acquireRelease(
      Effect.sync(() => registerEvents(EVENTS)),
      (cleanup) => Effect.sync(cleanup),
    );

    const emit = <T = void>(
      type: string,
      detail?: T,
      target: EventTarget = window,
    ) =>
      Effect.sync(() => {
        target.dispatchEvent(new CustomEvent(type, { detail }));
      });

    return EventRegistry.of({
      emit,
    });
  }),
);
