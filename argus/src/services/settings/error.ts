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
