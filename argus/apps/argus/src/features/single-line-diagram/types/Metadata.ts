/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Schema } from "effect";

export const Component = Schema.Struct({
  type: Schema.String,
  size: Schema.Struct({
    width: Schema.Number,
    height: Schema.Number,
  }),
  styleClass: Schema.optional(Schema.String),
  anchorPoints: Schema.optional(
    Schema.Array(
      Schema.Struct({
        orientation: Schema.String,
      }),
    ),
  ),
  transformations: Schema.optional(
    Schema.Record({
      key: Schema.String,
      value: Schema.String,
    }),
  ),
});

export const NodeLabelInfo = Schema.Struct({
  id: Schema.String,
  positionName: Schema.String,
  userDefinedId: Schema.optional(Schema.String),
});

export const Node = Schema.Struct({
  id: Schema.String,
  vid: Schema.String,
  unescapedId: Schema.optional(Schema.String),
  nextVId: Schema.optional(Schema.String),
  componentType: Schema.optional(Schema.String),
  open: Schema.Boolean,
  vlabel: Schema.Boolean,
  equipmentId: Schema.optional(Schema.String),
  direction: Schema.optional(Schema.String),
  labels: Schema.optional(Schema.Array(NodeLabelInfo)),
});

export const FeederInfo = Schema.Struct({
  id: Schema.String,
  equipmentId: Schema.String,
  side: Schema.optional(Schema.String),
  componentType: Schema.String,
});

export const Padding = Schema.Struct({
  left: Schema.Number,
  top: Schema.Number,
  right: Schema.Number,
  bottom: Schema.Number,
});

export const Metadata = Schema.Struct({
  components: Schema.Array(Component),
  nodes: Schema.Array(Node),
  lines: Schema.Array(Schema.Unknown),
  feederInfos: Schema.Array(FeederInfo),
  busInfos: Schema.Array(Schema.Unknown),
});

// eslint-disable-next-line no-redeclare
export type Metadata = Schema.Schema.Type<typeof Metadata>;
// eslint-disable-next-line no-redeclare
export type Component = Schema.Schema.Type<typeof Component>;
// eslint-disable-next-line no-redeclare
export type Node = Schema.Schema.Type<typeof Node>;
// eslint-disable-next-line no-redeclare
export type NodeLabelInfo = Schema.Schema.Type<typeof NodeLabelInfo>;
// eslint-disable-next-line no-redeclare
export type FeederInfo = Schema.Schema.Type<typeof FeederInfo>;
// eslint-disable-next-line no-redeclare
export type Padding = Schema.Schema.Type<typeof Padding>;
