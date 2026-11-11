/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Schema } from "effect";

export class ExtensionNotFoundError extends Schema.TaggedError<ExtensionNotFoundError>()(
  "ExtensionNotFoundError",
  { extensionId: Schema.String },
) {}

export class TauriInvokeError extends Schema.TaggedError<TauriInvokeError>()(
  "TauriInvokeError",
  { method: Schema.String, cause: Schema.Unknown },
) {}
