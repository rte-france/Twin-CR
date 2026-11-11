/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { invoke } from "@tauri-apps/api/core";

export interface AppConfig {
  keycloak_url: string;
  keycloak_realm: string;
  keycloak_client_id: string;
  session_manager_url: string;
  lobby_url: string;
  environment: "development" | "staging" | "production";
  api_url: string;
  api_token: string;
  oauth_dev_port: number;
}

let config: AppConfig | null = null;
let configLoaded = false;

export async function initArgusConfig() {
  if (configLoaded) return;

  config = await invoke<AppConfig>("get_config");
  configLoaded = true;
}

export function getArgusConfig(): AppConfig {
  if (!config) {
    throw new Error("Configuration not initialized");
  }
  return config;
}
