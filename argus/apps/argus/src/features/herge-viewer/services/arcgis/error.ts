/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Data } from "effect";
import type { HergeError } from "@/services/herge";

export class ArcGisParseError extends Data.TaggedError("ArcGisParseError")<{
  message: string;
}> {}
export class ArcGisCacheError extends Data.TaggedError("ArcGisCacheError")<{
  message: string;
}> {}

export type ArcGisError = ArcGisParseError | ArcGisCacheError | HergeError;
