/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Data } from "effect";

export class UnauthorizedUrl extends Data.TaggedError("UnauthorizedUrl")<{
  message: string;
}> {}

export class NetworkFail extends Data.TaggedError("NetworkFail")<{
  reason: string;
  endpoint?: string;
}> {}

export class HttpError extends Data.TaggedError("HttpError")<{
  status: number;
  endpoint?: string;
  message?: string;
}> {}

export class NotConnected extends Data.TaggedError("NotConnected") {}

export class Aborted extends Data.TaggedError("Aborted") {}

export type HergeError =
  | UnauthorizedUrl
  | NetworkFail
  | HttpError
  | NotConnected
  | Aborted
  | Error;

export const parseTauriError = (raw: any): HergeError => {
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

      case "ActorClosed":
      case "InvalidState":
      case "ConfigError":
      case "InternalError":
      case "UnauthorizedUrl":
        return new UnauthorizedUrl({ message: String(payload) });

      case "DataFormatError":
        return new Error(`Data format error: ${payload.reason}`);

      case "Aborted":
        return new Aborted();
    }

    return new Error(`Tauri Error: ${JSON.stringify(current)}`);
  }

  return new Error(String(raw));
};
