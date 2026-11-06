/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Data } from "effect";

export class NetworkFail extends Data.TaggedError("NetworkFail")<{
  reason: string;
  endpoint?: string;
}> {}
export class HttpError extends Data.TaggedError("HttpError")<{
  status: number;
  endpoint?: string;
  message?: string;
}> {}
export class SystemDead extends Data.TaggedError("SystemDead")<{
  reason: string;
}> {}
export class NotConnected extends Data.TaggedError("NotConnected") {}
export class Aborted extends Data.TaggedError("Aborted") {}
export class InvalidState extends Data.TaggedError("InvalidState")<{
  message: string;
}> {}

export type ScadaError =
  | NetworkFail
  | HttpError
  | SystemDead
  | NotConnected
  | Aborted
  | InvalidState
  | Error;

export const parseScadaError = (raw: any): ScadaError => {
  let current = raw;

  while (current && typeof current === "object" && "_tag" in current) {
    if (current._tag === "ServerManager" || current._tag === "HttpClient") {
      current = current.message;
    } else {
      break;
    }
  }

  if (current && typeof current === "object" && "_tag" in current) {
    const payload = current.message || {};

    switch (current._tag) {
      case "HttpError":
      case "ApiError":
        return new HttpError({
          status: payload.status,
          endpoint: payload.endpoint,
          message: payload.message || "Request failed",
        });
      case "NetworkFailure":
        return new NetworkFail({
          reason: payload.reason,
          endpoint: payload.endpoint,
        });
      case "NotConnected":
        return new NotConnected();
      case "InvalidState":
        return new InvalidState({
          message: typeof payload === "string" ? payload : "État Invalide",
        });
      case "ActorClosed":
      case "ConfigError":
      case "InternalError":
        return new SystemDead({
          reason: typeof payload === "string" ? payload : current._tag,
        });
      case "Aborted":
        return new Aborted();
    }

    return new Error(`Tauri Error: ${JSON.stringify(current)}`);
  }

  return new Error(typeof raw === "object" ? JSON.stringify(raw) : String(raw));
};

export interface GmTask {
  req_id: string;
  method: string;
  endpoint: string;
}
