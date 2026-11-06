/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, expect, it } from "vitest";
import { makeEndpointUri } from "@/services/http-client";

describe("makeEndpointUri", () => {
  it("should format correctly with both arguments", () => {
    expect(makeEndpointUri("/api/v1/users", "my-ext")).toBe(
      "my-ext://api/v1/users",
    );
    expect(makeEndpointUri("api/v1/users", "my-ext")).toBe(
      "my-ext://api/v1/users",
    );
    expect(makeEndpointUri("api/v1/users", "my-ext:endpoint")).toBe(
      "my-ext:endpoint://api/v1/users",
    );
  });

  it("should work in curried mode", () => {
    const withExt = makeEndpointUri("my-ext");
    expect(withExt("/api/v1/users")).toBe("my-ext://api/v1/users");
  });
});
