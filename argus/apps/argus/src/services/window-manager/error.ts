/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Data } from "effect";

export class WindowError extends Data.TaggedError("WindowError")<{
  message: string;
}> {}

export const parseWindowError = (raw: any): WindowError => {
  return new WindowError({ message: String(raw) });
};
