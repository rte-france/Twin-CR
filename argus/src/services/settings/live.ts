import { Context, Effect, Layer, Ref } from "effect";
import { listen } from "@tauri-apps/api/event";

import { type SettingsType } from "./schemas";
import { getSettingsCommand, patchSettingsCommand } from "./api";
import { type SettingsService } from "./service";

export class SettingsTag extends Context.Tag("Settings")<
  SettingsTag,
  SettingsService
>() {}

export const SettingsLive = Layer.scoped(
  SettingsTag,
  Effect.gen(function* () {
    const currentSettings = yield* Ref.make<SettingsType>({});

    const loadSettings = getSettingsCommand().pipe(
      Effect.tap((settings) => Ref.set(currentSettings, settings)),
      Effect.withSpan("SettingsService.loadSettings"),
    );

    const patchSettings = (patch: Record<string, any>) =>
      patchSettingsCommand({ patch }).pipe(
        Effect.tap((updated) => Ref.set(currentSettings, updated)),
        Effect.withSpan("SettingsService.patchSettings"),
      );

    // Initial load on layer acquisition
    yield* loadSettings.pipe(Effect.ignore);

    // Listen to external modifications of settings.json on disk
    yield* Effect.acquireRelease(
      Effect.tryPromise(() =>
        listen<SettingsType>("settings-changed", (event) => {
          Effect.runPromise(Ref.set(currentSettings, event.payload));
        }),
      ),
      (unlisten) => Effect.sync(() => unlisten()),
    ).pipe(Effect.ignore);

    return SettingsTag.of({
      currentSettings,
      loadSettings,
      patchSettings,
    });
  }),
);
