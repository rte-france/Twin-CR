/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface ParamInfo {
  type: "double" | "bool";
  description: string;
  default?: number | boolean;
}

export interface FunctionEntry {
  description: string;
  parameters: Record<string, ParamInfo>;
}

export type FunctionsSchema = Record<string, Record<string, FunctionEntry>>;

import schemaJson from "./functionsSchema.json";
export const schema = schemaJson as FunctionsSchema;
