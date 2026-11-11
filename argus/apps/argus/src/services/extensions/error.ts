/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Data } from "effect";

export class ExtensionDirError extends Data.TaggedError("ExtensionDirError")<{
  message: string;
}> {}
export class ManifestError extends Data.TaggedError("ManifestError")<{
  message: string;
}> {}
export class ExtensionNotFound extends Data.TaggedError("ExtensionNotFound")<{
  message: string;
}> {}
export class WasmerRuntimeError extends Data.TaggedError("WasmerRuntimeError")<{
  message: string;
}> {}
export class ExecutionFailed extends Data.TaggedError("ExecutionFailed")<{
  message: string;
}> {}
export class FunctionNotFound extends Data.TaggedError("FunctionNotFound")<{
  name: string;
  message: string;
}> {}
export class ActorClosed extends Data.TaggedError("ActorClosed") {}
export class Aborted extends Data.TaggedError("Aborted") {}

export type ExtensionError =
  | ExtensionDirError
  | ManifestError
  | ExtensionNotFound
  | WasmerRuntimeError
  | ExecutionFailed
  | FunctionNotFound
  | ActorClosed
  | Aborted
  | Error;

export const parseExtensionError = (raw: any): ExtensionError => {
  if (raw instanceof Error) return raw;
  if (typeof raw !== "object" || raw === null) return new Error(String(raw));

  const tag = raw._tag;
  const msg = raw.message || "Unknown extension error";

  switch (tag) {
    case "Directory":
      return new ExtensionDirError({ message: msg });
    case "Manifest":
      return new ManifestError({ message: msg });
    case "ExtensionNotFound":
      return new ExtensionNotFound({ message: msg });
    case "WasmerRuntime":
      return new WasmerRuntimeError({ message: msg });
    case "ExecutionFailed":
      return new ExecutionFailed({ message: msg });
    case "FunctionNotFound":
      return new FunctionNotFound({ name: raw.name || "", message: msg });
    case "ActorClosed":
      return new ActorClosed();
    case "Aborted":
      return new Aborted();
    default:
      return new Error(`Tauri Extension Error: ${JSON.stringify(raw)}`);
  }
};
