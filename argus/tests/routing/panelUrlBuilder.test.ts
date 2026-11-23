/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect } from "vitest";
import { buildPanelRoute } from "@/app/layout/shell/utils";

describe("buildPanelRoute", () => {
  it("builds a complete URL with panel state and parameters", () => {
    const route = buildPanelRoute({
      id: "panel-123",
      title: "Mon Panneau",
      viewType: "dsl-editor",
      entryUrl: "plugin://localhost/entry.js",
      isLocalFile: true,
      props: { file: "test.dsl" },
    });

    expect(route).toContain("/panels/panel-123?");
    expect(route).toContain("detached=true");
    expect(route).toContain("viewType=dsl-editor");
    expect(route).toContain("title=Mon+Panneau");
    expect(route).toContain("entryUrl=plugin%3A%2F%2Flocalhost%2Fentry.js");
    expect(route).toContain("isLocalFile=true");
    expect(route).toContain('props=%7B%22file%22%3A%22test.dsl%22%7D');
  });
});
