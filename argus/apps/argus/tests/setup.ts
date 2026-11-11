/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { beforeAll, beforeEach, afterEach } from "vitest";
import { mockIPC, clearMocks } from "@tauri-apps/api/mocks";
import { randomFillSync, randomUUID } from "crypto";
import { allHandlers, resetAllMocks } from "./mock";

beforeAll(() => {
  // Ensure Node globals match jsdom window
  if (typeof window !== "undefined") {
    window.AbortSignal = globalThis.AbortSignal;
    window.AbortController = globalThis.AbortController;
    window.Request = globalThis.Request;
    window.Response = globalThis.Response;
    window.Headers = globalThis.Headers;
    window.Blob = globalThis.Blob;
    window.FormData = globalThis.FormData;
    if (typeof globalThis.File !== "undefined") {
      window.File = globalThis.File;
      (global as any).File = globalThis.File;
    }
  }

  Object.defineProperty(window, "crypto", {
    value: {
      getRandomValues: (buffer: any) => randomFillSync(buffer),
      randomUUID: () => randomUUID(),
    },
  });
});

beforeEach(() => {
  resetAllMocks();

  mockIPC((cmd, args) => {
    const handler = allHandlers[cmd];
    if (handler) {
      return handler(args);
    }
    throw new Error(`[Tauri Mock] Command not found: ${cmd}`);
  });
});

afterEach(() => {
  clearMocks();
});
