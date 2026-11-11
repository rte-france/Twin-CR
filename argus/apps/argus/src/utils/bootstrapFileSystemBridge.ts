/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Cause, Effect, Exit } from "effect";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { FileSystemService } from "@/services/file-system";

export const bootstrapFileSystemBridge = () => {
  const runtime = getSystemRuntime();

  const argusFsBridge = {
    execute: async (
      method: "showOpenFilePicker" | "showDirectoryPicker",
      args: any[],
    ) => {
      const exit = await runtime.runPromiseExit(
        Effect.gen(function* () {
          const fs = yield* FileSystemService;
          if (method === "showOpenFilePicker") {
            return yield* fs.showOpenFilePicker(args[0]);
          }
          return yield* fs.showDirectoryPicker(args[0]);
        }),
      );

      if (Exit.isSuccess(exit)) return exit.value;

      const failure = Cause.failureOption(exit.cause);
      if (failure._tag === "Some" && (failure.value as any)?._tag === "UserAbortError") {
        throw new DOMException("The user aborted a request.", "AbortError");
      }

      if (Cause.isInterruptedOnly(exit.cause)) {
        throw new DOMException("The operation was aborted", "AbortError");
      }

      throw Cause.squash(exit.cause);
    },
  };

  window.dispatchEvent(
    new CustomEvent("argus:fs-bridge-ready", { detail: argusFsBridge }),
  );
};
