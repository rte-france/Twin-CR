/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect, vi, beforeEach } from "vitest";
import { Effect, Layer } from "effect";
import { WindowManager, WindowManagerLive } from "@/services/window-manager";
import * as core from "@tauri-apps/api/core";
import * as windowApi from "@tauri-apps/api/window";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
}));

vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: vi.fn(() => ({ label: "test_label" })),
}));

vi.mock("@tauri-apps/api/event", () => ({
  emit: vi.fn(),
  listen: vi.fn(),
}));

describe("WindowManager Service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should get current window label", async () => {
    const program = Effect.gen(function* () {
      const wm = yield* WindowManager;
      return yield* wm.getCurrentLabel();
    }).pipe(Effect.provide(WindowManagerLive));

    const result = await Effect.runPromise(program);
    expect(result).toBe("test_label");
  });

  it("should identify if current window is main", async () => {
    const program = Effect.gen(function* () {
      const wm = yield* WindowManager;
      return yield* wm.isMain();
    }).pipe(Effect.provide(WindowManagerLive));

    const result = await Effect.runPromise(program);
    expect(result).toBe(false);
  });

  it("should invoke create_child_window with current label as parent", async () => {
    const mockInvoke = vi.mocked(core.invoke);
    mockInvoke.mockResolvedValueOnce(undefined as never);

    const program = Effect.gen(function* () {
      const wm = yield* WindowManager;
      yield* wm.createChildFromCurrent("Child Title", "/panels/test");
    }).pipe(Effect.provide(WindowManagerLive));

    await Effect.runPromise(program);

    expect(mockInvoke).toHaveBeenCalledWith("create_child_window", {
      parentLabel: "test_label",
      title: "Child Title",
      route: "/panels/test",
    });
  });

  it("should invoke create_parent_window with title and route", async () => {
    const mockInvoke = vi.mocked(core.invoke);
    mockInvoke.mockResolvedValueOnce(undefined as never);

    const program = Effect.gen(function* () {
      const wm = yield* WindowManager;
      yield* wm.createParent("Parent Title", "/home");
    }).pipe(Effect.provide(WindowManagerLive));

    await Effect.runPromise(program);

    expect(mockInvoke).toHaveBeenCalledWith("create_parent_window", {
      title: "Parent Title",
      route: "/home",
    });
  });
});
