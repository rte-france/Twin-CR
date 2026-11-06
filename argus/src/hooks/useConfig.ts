/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { Effect, Redacted } from "effect";
import { ConfigService, getArgusConfig, type AppConfig } from "@/services/config";
import { getSystemRuntime } from "@/utils/getSystemRuntime";

const [configSignal, setConfigSignal] = createSignal<AppConfig | null>(null);

const initConfigProgram = Effect.gen(function* () {
  const service = yield* ConfigService;
  return service.config;
});

let isInitializing = false;

const initConfig = () => {
  if (isInitializing) return;
  isInitializing = true;

  getSystemRuntime()
    .runPromise(initConfigProgram)
    .then((cfg) => {
      const savedKeycloakUrl = sessionStorage.getItem("oauth_keycloak_url");
      if (savedKeycloakUrl) {
        setConfigSignal({ ...cfg, keycloakUrl: savedKeycloakUrl });
      } else {
        setConfigSignal(cfg);
      }
    })
    .catch((e) => {
      console.error("Failed to initialize configuration", e);
    });
};

export const useConfig = () => {
  initConfig();
  return configSignal;
};

export const setCustomKeycloakUrl = (url: string) => {
  sessionStorage.setItem("oauth_keycloak_url", url);
  const current = getConfigSync();
  setConfigSignal({ ...current, keycloakUrl: url });
};

export const getConfigSync = (): AppConfig => {
  initConfig();

  const current = configSignal();
  if (current) return current;

  const savedKeycloakUrl = sessionStorage.getItem("oauth_keycloak_url");

  return {
    environment: getArgusConfig().environment || "development",
    logLevel: "Debug",
    apiUrl: getArgusConfig().api_url,
    apiToken: Redacted.make(getArgusConfig().api_token),
    keycloakUrl: savedKeycloakUrl || getArgusConfig().keycloak_url,
    keycloakRealm: getArgusConfig().keycloak_realm,
    keycloakClientId: getArgusConfig().keycloak_client_id,
    oauthDevPort: Number(getArgusConfig().oauth_dev_port),
  };
};
