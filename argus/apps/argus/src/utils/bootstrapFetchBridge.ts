/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Cause, Effect, Exit } from "effect";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { FetchBridgeService } from "@/services/http-client";

export const bootstrapFetchBridge = () => {
  const runtime = getSystemRuntime();

  const argusHttpBridge = {
    execute: async (input: RequestInfo, init?: RequestInit) => {
      // Normalize null to undefined to satisfy Effect runtime options
      const signal = init?.signal ?? undefined;

      // Fast-path: bail out immediately if already aborted
      signal?.throwIfAborted();

      const exit = await runtime.runPromiseExit(
        Effect.gen(function* () {
          const bridge = yield* FetchBridgeService;
          return yield* bridge.execute(input, init);
        }),
        { signal }
      );

      if (Exit.isSuccess(exit)) return exit.value;

      // Map fiber interruptions to standard Fetch AbortError semantics
      if (Cause.isInterruptedOnly(exit.cause)) {
        if (signal?.aborted) {
          throw signal.reason;
        }
        throw new DOMException("The operation was aborted", "AbortError");
      }

      // Unwrap underlying domain or network defect
      throw Cause.squash(exit.cause);
    },
  };

  window.dispatchEvent(
    new CustomEvent("argus:bridge-ready", { detail: argusHttpBridge }),
  );
};
