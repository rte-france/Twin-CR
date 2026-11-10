/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import {
  Effect,
  Layer,
  Logger,
  LogLevel,
  Schema,
  pipe,
  Context,
  Data,
} from "effect";

export class ConfigurationError extends Data.TaggedError("ConfigurationError")<{
  readonly message: string;
  readonly cause?: unknown;
}> {}

export class RuntimeInitializationError extends Data.TaggedError(
  "RuntimeInitializationError",
)<{
  readonly message: string;
  readonly cause?: unknown;
}> {}

export const LogLevelSchema = Schema.Literal(
  "All",
  "Trace",
  "Debug",
  "Info",
  "Warning",
  "Error",
  "Fatal",
  "None",
);

export const AppConfigSchema = Schema.Struct({
  environment: Schema.Literal("development", "staging", "production"),
  logLevel: LogLevelSchema,
  apiUrl: Schema.String,
  apiToken: Schema.Redacted(Schema.String),
  keycloakUrl: Schema.String,
  keycloakRealm: Schema.String,
  keycloakClientId: Schema.String,
});

export type AppConfig = Schema.Schema.Type<typeof AppConfigSchema>;

export class ConfigService extends Context.Tag("App/ConfigService")<
  ConfigService,
  {
    readonly getConfig: Effect.Effect<AppConfig, ConfigurationError>;
    readonly config: AppConfig;
  }
>() {}

const decodeConfig = Schema.decodeUnknown(AppConfigSchema);

const readFromWindowGlobal = Effect.sync(
  () => (window as any).__APP_CONFIG__,
).pipe(
  Effect.flatMap((raw) =>
    raw
      ? Effect.succeed(raw)
      : Effect.fail(
          new ConfigurationError({
            message: "window.__APP_CONFIG__ is not set",
          }),
        ),
  ),
);

const readFromConfigJson = Effect.tryPromise({
  try: () =>
    fetch("/config.json").then((res) => {
      if (!res.ok) throw new Error(`config.json responded ${res.status}`);
      return res.json();
    }),
  catch: (cause) =>
    new ConfigurationError({
      message: "Failed to fetch /config.json",
      cause,
    }),
});

const readFromEnv = Effect.sync(() => ({
  environment: import.meta.env.MODE || "development",
  serviceName: "mfe-host-system",
  logLevel: "Debug",
  apiUrl: import.meta.env.VITE_API_URL || "http://localhost:3000",
  apiToken: import.meta.env.VITE_API_TOKEN || "",
  keycloakUrl:
    import.meta.env.VITE_KEYCLOAK_URL || "https://keycloak.localhost",
  keycloakRealm: import.meta.env.VITE_KEYCLOAK_REALM || "twineu",
  keycloakClientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "lobby",
}));

const readRawConfig = readFromWindowGlobal.pipe(
  Effect.orElse(() => readFromConfigJson),
  Effect.orElse(() => readFromEnv),
  Effect.withSpan("ConfigService.ReadRawConfig"),
);

export const ConfigServiceLive = Layer.effect(
  ConfigService,
  Effect.gen(function* () {
    yield* Effect.logDebug("Starting ConfigService initialization...");

    const rawConfig = yield* readRawConfig;

    const validConfig = yield* pipe(
      decodeConfig(rawConfig),
      Effect.mapError(
        (parseError) =>
          new ConfigurationError({
            message:
              "Échec de validation de la configuration (Schema Mismatch)",
            cause: parseError,
          }),
      ),
      Effect.withSpan("ConfigService.DecodeConfig", {
        attributes: {
          "config.raw_keys": Object.keys(rawConfig as object).join(","),
        },
      }),
    );

    yield* Effect.logInfo("Configuration loaded successfully").pipe(
      Effect.annotateLogs("app.environment", validConfig.environment),
      Effect.annotateLogs("app.log_level", validConfig.logLevel),
    );

    return ConfigService.of({
      getConfig: Effect.succeed(validConfig),
      config: validConfig,
    });
  }),
).pipe(Layer.withSpan("ConfigServiceLive.Initialize"));

export const ConfigLayer = Layer.empty.pipe(
  Layer.provideMerge(ConfigServiceLive),
  Layer.provide(Logger.minimumLogLevel(LogLevel.Debug)),
  Layer.provide(Logger.pretty),
);
