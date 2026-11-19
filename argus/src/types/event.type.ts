/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export type EventNode =
  | EventListenerOrEventListenerObject
  | {
      readonly listener: EventListenerOrEventListenerObject;
      readonly options?: boolean | AddEventListenerOptions;
    };

export interface EventTree {
  readonly [key: string]: EventNode | EventTree;
}

export interface FlattenedEvent {
  readonly type: string;
  readonly listener: EventListenerOrEventListenerObject;
  readonly options?: boolean | AddEventListenerOptions;
}
