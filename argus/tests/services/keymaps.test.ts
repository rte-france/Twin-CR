/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect } from "vitest";
import { flattenKeymaps } from "@/config/keymaps";
import type { KeymapTree } from "@/config/keymaps";

describe("flattenKeymaps", () => {
  it("flattens nested keymaps tree with colon delimiter", () => {
    const fn = () => {};
    const tree: KeymapTree = {
      application: {
        panel: {
          open_left: {
            description: "Open Left Panel",
            defaultKeys: ["mod+b"],
            handler: fn,
          },
        },
      },
    };

    const result = flattenKeymaps(tree);

    expect(result).toEqual([
      {
        id: "application:panel:open_left",
        name: "Open Left Panel",
        category: "application:panel",
        defaultKeys: ["mod+b"],
        handler: fn,
      },
    ]);
  });
});
