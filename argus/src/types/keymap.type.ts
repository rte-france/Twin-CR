/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export type CommandId = string;

export interface KeyBinding {
  readonly commandId: CommandId;
  readonly keyCombination: string;
}

export interface KeymapConfig {
  readonly [context: string]: readonly KeyBinding[];
}

export interface CommandDefinition {
  readonly id: CommandId;
  readonly name: string;
  readonly category: string;
  readonly defaultKeys: readonly string[];
  readonly handler: () => void | Promise<void>;
}
