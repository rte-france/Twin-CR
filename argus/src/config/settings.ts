/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { SettingSectionDefinition } from "@/types/settings.type";

export const SETTINGS: SettingSectionDefinition[] = [
  {
    id: "network",
    title: "Network",
    description:
      "Configure proxy rules and network routing for Argus background workers.",
    fields: [
      {
        key: "proxy",
        label: "HTTP / HTTPS Proxy",
        description:
          "Proxy server URL used by HttpManager (e.g. http://127.0.0.1:8080).",
        type: "string",
        placeholder: "http://127.0.0.1"
      },
      {
        key: "no_proxy",
        label: "No Proxy Hosts",
        description:
          "Comma-separated list of hostnames or IPs bypassing the proxy.",
        type: "string[]",
        placeholder: "http://127.0.0.1"
      },
    ],
  },
  {
    id: "keycloak",
    title: "Keycloak",
    description: "Keycloak server for authentification",
    fields: [
      {
        key: "keycloak_url",
        label: "Keycloak Url",
        description: "Url of Keycloak server",
        type: "string",
        defaultValue: "https://localhost:8443",
      },
      {
        key: "keycloak_realm",
        label: "Keycloak Realm",
        description: "Realm of Keycloak",
        type: "string",
        defaultValue: "twincr",
      },
      {
        key: "keycloak_client_id",
        label: "Keycloak Client",
        description: "Client of Keycloak",
        type: "string",
        defaultValue: "session-manager-client",
      },
      {
        key: "oauth_dev_port",
        label: "OAuth Dev Port",
        description: "Port used for local OAuth redirect server in development",
        type: "number",
        defaultValue: 8005,
      },
    ],
  },
];

export const getDefaultSettings = (): Record<string, any> => {
  const defaults: Record<string, any> = {};
  for (const section of SETTINGS) {
    if (section.id === "network") {
      // Root fields for network (proxy, no_proxy) required by Rust Settings struct
      for (const field of section.fields) {
        defaults[field.key] = field.defaultValue ?? null;
      }
    } else {
      const sectionObj: Record<string, any> = {};
      for (const field of section.fields) {
        sectionObj[field.key] = field.defaultValue ?? null;
      }
      defaults[section.id] = sectionObj;
    }
  }
  return defaults;
};
