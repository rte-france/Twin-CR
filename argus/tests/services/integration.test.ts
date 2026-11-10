/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect } from "vitest";
import { Effect, Layer, Scope } from "effect";
import { EventRegistryLive } from "@/services/events";
import { KeymapSystemLive } from "@/services/keymaps";
import {
  setLeftToggleHandler,
  setDockviewInstance,
} from "@/app/layout/shell/actions";

const TestSystemLayer = Layer.merge(EventRegistryLive, KeymapSystemLive);

describe("Keymap & Event Integration", () => {
  it("triggers centralized shell handlers when keymap shortcut is pressed", async () => {
    const scope = await Effect.runPromise(Scope.make());
    await Effect.runPromise(Scope.extend(Layer.build(TestSystemLayer), scope));

    let leftPanelToggled = false;
    let tabClosed = false;

    setLeftToggleHandler(() => {
      leftPanelToggled = true;
    });

    const mockDockview: any = {
      activeGroup: {
        activePanel: {
          api: {
            close: () => {
              tabClosed = true;
            },
          },
        },
      },
    };
    setDockviewInstance(mockDockview);

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "b",
        ctrlKey: true,
        bubbles: true,
      }),
    );

    expect(leftPanelToggled).toBe(true);

    window.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "w",
        ctrlKey: true,
        bubbles: true,
      }),
    );

    expect(tabClosed).toBe(true);

    setLeftToggleHandler(null);
    setDockviewInstance(null);
    await Effect.runPromise(Scope.close(scope, Effect.void as any));
  });
});
