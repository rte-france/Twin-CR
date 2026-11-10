/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { WebviewWindow } from "@tauri-apps/api/webviewWindow";
import { emit, listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { Effect, Context, Layer, Stream } from "effect";
import { parseWindowError, WindowError } from "./error";
import { getCurrentWindow } from "@tauri-apps/api/window";

export interface WindowConfig {
  label: string;
  title: string;
  width?: number;
  height?: number;
}

export class WindowManager extends Context.Tag("WindowManager")<
  WindowManager,
  {
    readonly open: (
      config: WindowConfig,
    ) => Effect.Effect<WebviewWindow, WindowError>;
    readonly broadcast: <T>(
      eventName: string,
      payload: T,
    ) => Effect.Effect<void, WindowError>;
    readonly subscribe: <T>(eventName: string) => Stream.Stream<T, WindowError>;
    readonly getCurrentLabel: () => Effect.Effect<string>;
    readonly isMain: () => Effect.Effect<boolean>;
    readonly createParent: (
      title: string,
      route: string,
    ) => Effect.Effect<void, WindowError>;
    readonly createChildFromCurrent: (
      title: string,
      route: string,
    ) => Effect.Effect<void, WindowError>;
    readonly getParentLabel: () => Effect.Effect<string | null>;
  }
>() {}

export const WindowManagerLive = Layer.succeed(
  WindowManager,
  WindowManager.of({
    open: (config) =>
      Effect.try({
        try: () =>
          new WebviewWindow(config.label, {
            ...config,
            url: "index.html",
            decorations: false,
            titleBarStyle: "overlay",
            resizable: true,
          }),
        catch: parseWindowError,
      }),

    broadcast: (eventName, payload) =>
      Effect.tryPromise({
        try: () => emit(eventName, payload),
        catch: parseWindowError,
      }),

    subscribe: <T>(eventName: string) =>
      Stream.async<T, WindowError>((emit) => {
        const unlistenPromise = listen(eventName, (event: { payload: T }) => {
          emit.single(event.payload);
        });
        return Effect.promise(async () => {
          const unlisten = await unlistenPromise;
          unlisten();
        });
      }),

    getCurrentLabel: () => Effect.sync(() => getCurrentWindow().label),

    isMain: () => Effect.sync(() => getCurrentWindow().label === "main"),

    createParent: (title, route) =>
      Effect.tryPromise({
        try: () => invoke("create_parent_window", { title, route }),
        catch: parseWindowError,
      }),

    createChildFromCurrent: (title, route) =>
      Effect.gen(function* () {
        const currentLabel = getCurrentWindow().label;
        yield* Effect.tryPromise({
          try: () =>
            invoke("create_child_window", {
              parentLabel: currentLabel,
              title,
              route,
            }),
          catch: parseWindowError,
        });
      }),

    getParentLabel: () =>
      Effect.sync(() => {
        const params = new URLSearchParams(window.location.search);
        return params.get("parent");
      }),
  }),
);
