/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect, Stream, Chunk } from "effect";
import { HttpClientRequest, HttpClientError } from "@effect/platform";
import { mockIPC } from "@tauri-apps/api/mocks";

import { executeSSERequest } from "@/services/http-client";

describe("executeSSERequest", () => {
  it.effect("should read SSE stream and encode correctly", () =>
    Effect.gen(function* () {
      mockIPC((cmd, args: any) => {
        if (cmd === "sse") {
          const channel = args.onEvent;

          setTimeout(
            () => channel.onmessage('data: {"data": "chunk1"}\n\n'),
            10,
          );
          setTimeout(
            () => channel.onmessage('data: {"data": "chunk2"}\n\n'),
            20,
          );
          setTimeout(() => channel.onmessage("[CLOSE]"), 30);
        }
      });

      const req = HttpClientRequest.get("https://api.test/stream");
      const res = yield* executeSSERequest("client-1", "req-sse", req, {});

      expect(res.status).toBe(200);
      expect(res.headers["content-type"]).toBe("text/event-stream");

      const binaryChunks = yield* Stream.runCollect(res.stream);

      const decoder = new TextDecoder();
      const chunks = Chunk.toArray(binaryChunks).map((bytes) =>
        decoder.decode(bytes),
      );
      expect(chunks).toEqual([
        'data: {"data": "chunk1"}\n\n',
        'data: {"data": "chunk2"}\n\n',
      ]);
    }),
  );

  it.effect("should propagate error if stream emits ERROR", () =>
    Effect.gen(function* () {
      mockIPC((cmd, args: any) => {
        if (cmd === "sse") {
          const channel = args.onEvent;
          setTimeout(() => channel.onmessage("ERROR: Connection lost"), 10);
        }
      });

      const req = HttpClientRequest.get("https://api.test/stream");
      const res = yield* executeSSERequest("client-1", "req-err", req, {});

      const err = yield* Effect.flip(Stream.runCollect(res.stream));

      expect(err._tag).toBe("ResponseError");
      expect(String((err as HttpClientError.ResponseError).cause)).toContain(
        "ERROR: Connection lost",
      );
    }),
  );
});
