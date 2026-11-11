/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { invoke } from "@tauri-apps/api/core";
import { Effect, Context, Layer } from "effect";
import { getCurrentWindow } from "@tauri-apps/api/window";

export interface WindowError {
  _tag: "WindowError";
  message: string;
}

export class WindowBootstrapper extends Context.Tag("WindowBootstrapper")<
  WindowBootstrapper,
  {
    readonly createParent: (
      title: string,
      route: string,
    ) => Effect.Effect<void, WindowError>;
    readonly createChildFromCurrent: (
      title: string,
      route: string,
    ) => Effect.Effect<void, WindowError>;
    readonly getParentLabel: () => Effect.Effect<string | null>;
    readonly getCurrentLabel: () => Effect.Effect<string>;
  }
>() {}

export const WindowBootstrapperLive = Layer.succeed(
  WindowBootstrapper,
  WindowBootstrapper.of({
    createParent: (title, route) =>
      Effect.tryPromise({
        try: () => invoke("create_parent_window", { title, route }),
        catch: (e) =>
          ({ _tag: "WindowError", message: String(e) }) as WindowError,
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
          catch: (e) =>
            ({ _tag: "WindowError", message: String(e) }) as WindowError,
        });
      }),

    getParentLabel: () =>
      Effect.sync(() => {
        const params = new URLSearchParams(window.location.search);
        return params.get("parent");
      }),

    getCurrentLabel: () => Effect.sync(() => getCurrentWindow().label),
  }),
);
