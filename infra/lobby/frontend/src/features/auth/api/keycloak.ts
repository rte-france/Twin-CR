/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import Keycloak from "keycloak-js";
import { Data, Effect } from "effect";
import { ConfigService, ConfigLayer } from "@/services/config";

export class KeycloakInitializationError extends Data.TaggedError(
  "KeycloakInitializationError",
)<{
  readonly message: string;
  readonly cause?: unknown;
}> {}

export let kc: Keycloak;

export const initAuth = () =>
  Effect.runPromise(
    Effect.gen(function* () {
      const { config } = yield* ConfigService;

      kc = new Keycloak({
        url: config.keycloakUrl,
        realm: config.keycloakRealm,
        clientId: config.keycloakClientId,
      });

      return yield* Effect.tryPromise({
        try: () =>
          kc.init({
            onLoad: "login-required",
            pkceMethod: "S256",
            checkLoginIframe: false,
          }),
        catch: (cause) => {
          const errorMessage =
            cause instanceof Error ? cause.message : String(cause);

          console.error("Error Keycloak:", cause);

          return new KeycloakInitializationError({
            message: `Failed to initialize Keycloak: ${errorMessage}`,
            cause,
          });
        },
      });
    }).pipe(Effect.provide(ConfigLayer)),
  );
