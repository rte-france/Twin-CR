/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Effect, Ref } from "effect";
import { type SettingsError } from "./error";
import { type SettingsType } from "./schemas";

export interface SettingsService {
  readonly currentSettings: Ref.Ref<SettingsType>;

  readonly loadSettings: Effect.Effect<SettingsType, SettingsError>;

  readonly patchSettings: (
    patch: Record<string, any>,
  ) => Effect.Effect<SettingsType, SettingsError>;
}
