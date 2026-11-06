/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Schema } from "effect";

export const ExtensionUriSchema = Schema.String.pipe(
  Schema.filter((s) => s.includes("://"), {
    message: () =>
      "A ExtensionUriSchema must contain '://' (format: endpointAlias://path)",
  }),
  Schema.brand("ExtensionUri"),
);

export type ExtensionUri = Schema.Schema.Type<typeof ExtensionUriSchema>;

export const ExtensionUrlSchema = Schema.String.pipe(
  Schema.pattern(/^([a-z0-9_-]+):\/\/([a-z0-9_-]+)$/, {
    message: () => "baseUrl must respect format 'extensionId://endpointName'",
  }),
  Schema.brand("ExtensionUrl"),
);

export type ExtensionUrl = Schema.Schema.Type<typeof ExtensionUrlSchema>;
