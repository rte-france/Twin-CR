/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect, it } from "vitest";
import fc from "fast-check";
import { makeEndpointUri } from "@/services/http-client";

describe("makeEndpointUri - Property-Based Testing", () => {
  it("should always remove initial slash and concatenate correctly", () => {
    fc.assert(
      fc.property(fc.string({ minLength: 1 }), fc.string(), (alias, path) => {
        const result = makeEndpointUri(path, alias);
        const cleanPath = path.replace(/^\/+/, "");

        expect(result).toBe(`${alias}://${cleanPath}`);
        expect(result).not.toContain(":///");
      }),
    );
  });
});
