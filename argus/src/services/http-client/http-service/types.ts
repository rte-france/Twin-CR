/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface AllowedEndpoint {
  readonly endpoint: string;
  readonly base_url: string;
}

export interface ExtensionManifest {
  readonly id: string;
  readonly name: string;
  readonly allowed_endpoints: AllowedEndpoint[];
}

export interface TauriHttpResponse {
  status: number;
  headers: Record<string, string>;
  body: number[];
}
