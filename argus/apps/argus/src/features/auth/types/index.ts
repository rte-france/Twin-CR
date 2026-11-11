/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export type AuthBackendError =
  | { _tag: "ClientInit"; message: string }
  | { _tag: "Network"; message: string }
  | { _tag: "AuthenticationRefused"; message: string }
  | { _tag: "ResponseBody"; message: string };

export const isAuthBackendError = (err: unknown): err is AuthBackendError => {
  return (
    typeof err === "object" &&
    err !== null &&
    "_tag" in err &&
    typeof (err as Record<string, unknown>)._tag === "string" &&
    "message" in err &&
    typeof (err as Record<string, unknown>).message === "string"
  );
};

export const getAuthErrorMessage = (err: unknown): string => {
  if (isAuthBackendError(err)) {
    switch (err._tag) {
      case "Network":
        return `Network unavailable: ${err.message}`;
      case "AuthenticationRefused":
        return `Authentication refused: ${err.message}`;
      case "ClientInit":
        return `HTTP client initialization failed: ${err.message}`;
      case "ResponseBody":
        return `Invalid server response: ${err.message}`;
    }
  }

  if (err instanceof Error) {
    return err.message;
  }

  if (typeof err === "string") {
    return err;
  }

  return "An unexpected authentication error occurred.";
};
