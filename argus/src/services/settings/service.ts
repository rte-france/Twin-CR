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
