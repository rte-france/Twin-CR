/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Schema } from "effect";

export class SettingsIoError extends Schema.TaggedError<SettingsIoError>()(
  "Io",
  { message: Schema.String },
) {}

export class SettingsJsonError extends Schema.TaggedError<SettingsJsonError>()(
  "Json",
  { message: Schema.String },
) {}

export class SettingsGeneralError extends Schema.TaggedError<SettingsGeneralError>()(
  "General",
  { message: Schema.String },
) {}

export const SettingsErrorSchema = Schema.Union(
  SettingsIoError,
  SettingsJsonError,
  SettingsGeneralError,
);

export type SettingsError = Schema.Schema.Type<typeof SettingsErrorSchema>;
