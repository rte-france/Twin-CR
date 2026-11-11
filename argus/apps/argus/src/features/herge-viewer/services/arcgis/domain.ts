/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Schema } from "effect";

export const LegendResponseSchema = Schema.Struct({
  layers: Schema.Array(Schema.Any),
});

export const QueryFeaturesSchema = Schema.Struct({
  features: Schema.optionalWith(
    Schema.Array(
      Schema.Struct({
        attributes: Schema.Record({ key: Schema.String, value: Schema.Any }),
        geometry: Schema.optional(Schema.Any),
      }),
    ),
    { exact: true, default: () => [] },
  ),
});

export const IdentifyResponseSchema = Schema.Struct({
  results: Schema.optionalWith(Schema.Array(Schema.Any), {
    exact: true,
    default: () => [],
  }),
});
