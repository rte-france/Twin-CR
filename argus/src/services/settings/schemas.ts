import { Schema } from "effect";

export const SettingsSchema = Schema.Struct({
  proxy: Schema.optional(Schema.NullOr(Schema.String)),
  no_proxy: Schema.optional(Schema.NullOr(Schema.Array(Schema.String))),
}).pipe(Schema.extend(Schema.Record({ key: Schema.String, value: Schema.Any })));

export type SettingsType = Schema.Schema.Type<typeof SettingsSchema>;

export const PatchSettingsSchema = Schema.Struct({
  patch: Schema.Record({ key: Schema.String, value: Schema.Any }),
});

export type PatchSettings = Schema.Schema.Type<typeof PatchSettingsSchema>;
