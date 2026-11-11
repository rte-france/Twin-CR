/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect } from "vitest";
import { it } from "@effect/vitest";
import { Effect } from "effect";
import { HttpClientRequest } from "@effect/platform";
import fc from "fast-check";

import { executeStandardRequest } from "@/services/http-client";
import { mockClient } from "../mocks/MockHttpClient";

describe("executeStandardRequest - Property-Based Testing", () => {
  it.effect(
    "should correctly parse any combination of Status, Headers, and Body",
    () =>
      Effect.gen(function* () {
        yield* Effect.promise(() =>
          fc.assert(
            fc.asyncProperty(
              fc.integer({ min: 200, max: 599 }),
              // Map keys to lowercase to avoid case-insensitive collisions (e.g. "w" and "W")
              // which HTTP Headers combines with commas according to spec RFC 7230.
              fc
                .dictionary(
                  fc.stringMatching(/^[a-zA-Z0-9-]+$/),
                  fc.stringMatching(/^[a-zA-Z0-9_.-]+$/),
                )
                .map((dict) =>
                  Object.fromEntries(
                    Object.entries(dict).map(([k, v]) => [k.toLowerCase(), v]),
                  ),
                ),
              fc.string(),
              async (status, headers, bodyText) => {
                mockClient.setRoute("PUT", "https://api.test/fuzz", {
                  status,
                  headers,
                  body: bodyText,
                });

                const req = HttpClientRequest.put("https://api.test/fuzz");

                const response = await Effect.runPromise(
                  executeStandardRequest("fuzz-client", "req-fuzz", req, {}),
                );

                expect(response.status).toBe(status);

                for (const [key, value] of Object.entries(headers)) {
                  expect(response.headers[key.toLowerCase()]).toBe(value);
                }

                // Handle the expected behavior for statuses that strip bodies
                const parsedBody = await Effect.runPromise(response.text);
                const statusesWithNoBody = [204, 205, 304];

                if (statusesWithNoBody.includes(status)) {
                  expect(parsedBody).toBe("");
                } else {
                  expect(parsedBody).toBe(bodyText);
                }
              },
            ),
            { numRuns: 100 },
          ),
        );
      }),
  );
});
