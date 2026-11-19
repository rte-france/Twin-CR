/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect } from "vitest";
import { flattenKeymaps } from "@/services/keymaps/utils";
import type { KeymapTree } from "@/types/keymap.type";

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

describe("getEventString", () => {
  it("normalizes Backtab key event with shift into shift+tab", async () => {
    const { getEventString } = await import("@/services/keymaps/utils");
    const event = new KeyboardEvent("keydown", {
      key: "Backtab",
      shiftKey: true,
      ctrlKey: true,
    });
    expect(getEventString(event)).toBe("mod+shift+tab");
  });

  it("preserves standard browser keys like ArrowLeft and ArrowRight", async () => {
    const { getEventString } = await import("@/services/keymaps/utils");
    const leftEvent = new KeyboardEvent("keydown", {
      key: "ArrowLeft",
      ctrlKey: true,
    });
    expect(getEventString(leftEvent)).toBe("mod+arrowleft");

    const spaceEvent = new KeyboardEvent("keydown", {
      key: " ",
      ctrlKey: true,
    });
    expect(getEventString(spaceEvent)).toBe("mod+space");
  });

  it("returns modifier-only string for modifier keys alone without committing shortcut", async () => {
    const { getEventString } = await import("@/services/keymaps/utils");
    const shiftEvent = new KeyboardEvent("keydown", {
      key: "Shift",
      shiftKey: true,
    });
    expect(getEventString(shiftEvent)).toBe("shift");

    const ctrlEvent = new KeyboardEvent("keydown", {
      key: "Control",
      ctrlKey: true,
    });
    expect(getEventString(ctrlEvent)).toBe("mod");

    const altEvent = new KeyboardEvent("keydown", {
      key: "Alt",
      altKey: true,
    });
    expect(getEventString(altEvent)).toBe("alt");
  });
});

describe("KeymapItem modifier recording behavior", () => {
  it("resets live preview on keyup when modifier is released without a main key", async () => {
    const { render } = await import("solid-js/web");
    const { KeymapItem } = await import("@/features/keymaps/components/KeymapItem");
    const { getEventString } = await import("@/services/keymaps/utils");

    let updatedShortcut = "";
    const container = document.createElement("div");
    document.body.appendChild(container);

    const dispose = render(
      () =>
        KeymapItem({
          command: {
            id: "test:cmd",
            name: "Test Command",
            category: "test",
            defaultKeys: ["mod+k"],
            handler: () => {},
          },
          currentKey: "",
          isSaving: false,
          onUpdate: async (key: string) => {
            updatedShortcut = key;
          },
          getEventString: (e: KeyboardEvent) => getEventString(e, "logical"),
        }),
      container,
    );

    // Enter recording mode
    const editBtn = container.querySelector("button[title='Edit shortcut']") as HTMLButtonElement;
    editBtn.click();

    const inputDiv = container.querySelector("div[tabindex='0']") as HTMLDivElement;
    expect(inputDiv).not.toBeNull();

    // Press Shift alone (keydown) -> displays preview
    inputDiv.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "Shift",
        shiftKey: true,
        bubbles: true,
      }),
    );
    expect(inputDiv.textContent).toContain("shift");
    expect(updatedShortcut).toBe("");

    // Release Shift alone (keyup) -> resets preview
    inputDiv.dispatchEvent(
      new KeyboardEvent("keyup", {
        key: "Shift",
        bubbles: true,
      }),
    );
    expect(inputDiv.textContent).not.toContain("shift");
    expect(inputDiv.textContent).toContain("Press combination");
    expect(updatedShortcut).toBe("");

    // Now press Ctrl + K -> commits shortcut
    inputDiv.dispatchEvent(
      new KeyboardEvent("keydown", {
        key: "k",
        ctrlKey: true,
        bubbles: true,
      }),
    );
    expect(updatedShortcut).toBe("mod+k");

    dispose();
    container.remove();
  });

  it("supports controlled recording mode to allow only one input open at a time", async () => {
    const { render } = await import("solid-js/web");
    const { createSignal } = await import("solid-js");
    const { KeymapItem } = await import("@/features/keymaps/components/KeymapItem");
    const { getEventString } = await import("@/services/keymaps/utils");

    const [activeId, setActiveId] = createSignal<string | null>(null);
    const container = document.createElement("div");
    document.body.appendChild(container);

    const dispose = render(
      () => [
        KeymapItem({
          command: {
            id: "cmd:1",
            name: "Command 1",
            category: "test",
            defaultKeys: ["mod+1"],
            handler: () => {},
          },
          currentKey: "",
          isSaving: false,
          get isRecording() {
            return activeId() === "cmd:1";
          },
          onStartRecording: () => setActiveId("cmd:1"),
          onStopRecording: () => setActiveId(null),
          onUpdate: async () => {},
          getEventString: (e) => getEventString(e, "logical"),
        }),
        KeymapItem({
          command: {
            id: "cmd:2",
            name: "Command 2",
            category: "test",
            defaultKeys: ["mod+2"],
            handler: () => {},
          },
          currentKey: "",
          isSaving: false,
          get isRecording() {
            return activeId() === "cmd:2";
          },
          onStartRecording: () => setActiveId("cmd:2"),
          onStopRecording: () => setActiveId(null),
          onUpdate: async () => {},
          getEventString: (e) => getEventString(e, "logical"),
        }),
      ],
      container,
    );

    const editButtons = container.querySelectorAll("button[title='Edit shortcut']");
    expect(editButtons).toHaveLength(2);

    // Click edit on command 1
    (editButtons[0] as HTMLButtonElement).click();
    expect(container.querySelectorAll("div[tabindex='0']")).toHaveLength(1);
    expect(activeId()).toBe("cmd:1");

    // Click edit on command 2 -> closes command 1 and opens command 2
    const remainingEditBtn = container.querySelector("button[title='Edit shortcut']") as HTMLButtonElement;
    remainingEditBtn.click();
    expect(container.querySelectorAll("div[tabindex='0']")).toHaveLength(1);
    expect(activeId()).toBe("cmd:2");

    dispose();
    container.remove();
  });
});
