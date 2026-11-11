/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export * from "./config";

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
import { getArgusConfig, initArgusConfig } from "./config";

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
  oauthDevPort: Schema.optionalWith(Schema.Number, { default: () => 8005 }),
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

const readFromEnv = Effect.tryPromise({
  try: async () => {
    await initArgusConfig();

    const cfg = getArgusConfig();

    return {
      environment: cfg.environment,
      serviceName: "mfe-host-system",
      logLevel: "Debug",
      apiUrl: cfg.api_url,
      apiToken: cfg.api_token,
      keycloakUrl: cfg.keycloak_url,
      keycloakRealm: cfg.keycloak_realm,
      keycloakClientId: cfg.keycloak_client_id,
      oauthDevPort: Number(cfg.oauth_dev_port),
    };
  },
  catch: (cause) =>
    new ConfigurationError({
      message: "Failed to load config",
      cause,
    }),
});

const readRawConfig = readFromWindowGlobal.pipe(
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
            message: "Configuration Failed (Schema Mismatch)",
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
