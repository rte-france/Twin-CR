/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  SettingsError,
  SettingsErrorSchema,
  SettingsGeneralError,
} from "./error";
import {
  PatchSettings,
  PatchSettingsSchema,
  SettingsSchema,
  SettingsType,
} from "./schemas";
import { Effect, Schema } from "effect";
import { invoke } from "@tauri-apps/api/core";

const toGeneralError = (cause: unknown): SettingsGeneralError =>
  new SettingsGeneralError({
    message: cause instanceof Error ? cause.message : String(cause),
  });

// TODO: use Client Tauri to describe a tauri command
const invokeCommand = <A, I, Args extends Record<string, unknown> | undefined>(
  command: string,
  responseSchema: Schema.Schema<A, I>,
  args?: Args,
): Effect.Effect<A, SettingsError> =>
  Effect.tryPromise({
    try: () => invoke<unknown>(command, args ?? {}),
    catch: (rawError): SettingsError => {
      const parsed = Schema.decodeUnknownEither(SettingsErrorSchema)(rawError);
      return parsed._tag === "Right" ? parsed.right : toGeneralError(rawError);
    },
  }).pipe(
    Effect.flatMap((rawResponse) =>
      Schema.decodeUnknown(responseSchema)(rawResponse).pipe(
        Effect.mapError(toGeneralError),
      ),
    ),
  );

export const getSettingsCommand = (): Effect.Effect<
  SettingsType,
  SettingsError
> => invokeCommand("get_settings", SettingsSchema);

export const patchSettingsCommand = (
  args: PatchSettings,
): Effect.Effect<SettingsType, SettingsError> =>
  Schema.encode(PatchSettingsSchema)(args).pipe(
    Effect.mapError(toGeneralError),
    Effect.flatMap((encodedArgs) =>
      invokeCommand("patch_settings", SettingsSchema, encodedArgs),
    ),
  );
