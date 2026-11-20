/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Chunk, Effect, Stream } from "effect";

import { sseData } from "@/services/http-client";

const bytes = (...parts: string[]) =>
  Stream.fromIterable(parts.map((p) => new TextEncoder().encode(p)));

describe("sseData", () => {
  it.effect("yields the data of each event, across arbitrary chunk boundaries", () =>
    Effect.gen(function* () {
      const out = yield* Stream.runCollect(
        sseData(
          bytes(
            'id: 1\ndata: {"a":',
            "1}\n\n: comment\n\nevent: x\r\ndata: line1\r\ndata:line2\r\n\r\n",
            "data: last\n\n",
          ),
        ),
      );
      expect(Chunk.toArray(out)).toEqual(['{"a":1}', "line1\nline2", "last"]);
    }),
  );

  it.effect("drops an unterminated trailing event", () =>
    Effect.gen(function* () {
      const out = yield* Stream.runCollect(sseData(bytes("data: a\n\ndata: b")));
      expect(Chunk.toArray(out)).toEqual(["a"]);
    }),
  );
});
