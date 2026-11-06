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

export type GmError =
  | NetworkFail
  | HttpError
  | SystemDead
  | NotConnected
  | Aborted
  | InvalidState
  | Error;

// Every Rust error enum here uses #[serde(tag = "_tag", content = "message")] (adjacent tagging):
// a struct variant serializes as {_tag, message: {..named fields}}, a tuple variant (e.g. a single
// String, or a transparent #[from] wrapper around another tagged error) as {_tag, message: <that
// single value>}, and a unit variant as bare {_tag} with no "message" key at all. So a variant's own
// fields always live one level down, under "message" — never spread alongside "_tag" directly.
export const parseGmError = (raw: any): GmError => {
  if (raw instanceof Error) return raw;

  if (typeof raw === "string") return new Error(raw);

  if (!raw || typeof raw !== "object") {
    return new Error(String(raw));
  }

  let node = raw;

  // Transparent #[from] wrapper variants (ServerManager/DatabaseManager tuple variants wrapping
  // another tagged error) nest that error one level deeper under "message"; unwrap through as many
  // such layers as present.
  while (
    node &&
    typeof node === "object" &&
    "_tag" in node &&
    node.message &&
    typeof node.message === "object" &&
    "_tag" in node.message
  ) {
    node = node.message;
  }

  if (!node || typeof node !== "object" || !("_tag" in node)) {
    return new Error(`Tauri Error: ${JSON.stringify(raw)}`);
  }

  const tag = node._tag;
  const content = node.message;
  const fields = content && typeof content === "object" ? content : {};

  switch (tag) {
    case "HttpError":
    case "ApiError":
      return new HttpError({
        status: fields.status || 500,
        endpoint: fields.endpoint,
        message:
          (typeof fields.message === "string" && fields.message) ||
          (typeof content === "string" && content) ||
          "Request failed",
      });

    case "NetworkFailure":
      return new NetworkFail({
        reason:
          fields.reason ||
          (typeof content === "string" && content) ||
          "Network failure",
        endpoint: fields.endpoint,
      });

    case "NotConnected":
      return new NotConnected();

    case "InvalidState":
      return new InvalidState({
        message: typeof content === "string" ? content : "État Invalide",
      });

    case "ActorClosed":
    case "ConfigError":
    case "InternalError":
      return new SystemDead({
        reason:
          fields.reason ||
          (typeof content === "string" && content) ||
          tag,
      });

    case "Aborted":
      return new Aborted();

    case "HttpClient":
    case "ServerManager":
    case "DatabaseManager":
      return new NetworkFail({
        reason:
          (typeof content === "string" && content) ||
          fields.message ||
          "Network Error",
      });
  }

  return new Error(`Tauri Error: ${JSON.stringify(raw)}`);
};

export interface GmTask {
  req_id: string;
  method: string;
  endpoint: string;
}
