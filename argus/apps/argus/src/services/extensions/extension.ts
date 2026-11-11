/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer, Ref, Array } from "effect";
import { invoke } from "@tauri-apps/api/core";
import { parseExtensionError, type ExtensionError } from "./error";

export interface ExtensionWidget {
  name: string;
  element: string;
  zone: string;
}

export interface ExtensionManifest {
  id: string;
  name: string;
  version: string;
  description?: string;
  entry: string;
  wasm_entry?: string;
  widgets: ExtensionWidget[];
}

export interface ExtensionService {
  readonly mountedExtensions: Ref.Ref<ExtensionManifest[]>;

  readonly mountAll: Effect.Effect<void, ExtensionError>;

  readonly executeWasm: (
    pluginId: string,
    funcName: string,
  ) => Effect.Effect<any, ExtensionError>;

  readonly installExtension: (
    zipPath: string,
  ) => Effect.Effect<ExtensionManifest, ExtensionError>;

  readonly updateExtension: (
    pluginId: string,
    zipPath: string,
  ) => Effect.Effect<ExtensionManifest, ExtensionError>;

  readonly deleteExtension: (
    pluginId: string,
  ) => Effect.Effect<void, ExtensionError>;
}

export class Extension extends Context.Tag("Extension")<
  Extension,
  ExtensionService
>() {}

export const ExtensionLive = Layer.effect(
  Extension,
  Effect.gen(function* () {
    const mountedExtensions = yield* Ref.make<ExtensionManifest[]>([]);

    const loadScript = (manifest: ExtensionManifest) =>
      Effect.gen(function* () {
        const scriptId = `extension-${manifest.id}`;

        yield* Effect.sync(() => {
          const oldScript = document.getElementById(scriptId);
          if (oldScript) oldScript.remove();

          const script = document.createElement("script");
          script.id = scriptId;
          script.type = "module";
          script.src = `plugin://localhost/${manifest.id}/${manifest.entry}?t=${Date.now()}`;
          document.head.appendChild(script);
        });

        yield* Effect.logInfo(`[Extension] Hot Reloaded: ${manifest.id}`);
      });

    return Extension.of({
      mountedExtensions,

      mountAll: Effect.gen(function* () {
        yield* Effect.logDebug("Scanning for available extensions...");

        const manifests = yield* Effect.tryPromise({
          try: () => invoke<ExtensionManifest[]>("get_available_extensions"),
          catch: parseExtensionError,
        });

        yield* Effect.all(
          Array.map(manifests, (m) => loadScript(m)),
          { concurrency: "unbounded" },
        );

        yield* Ref.set(mountedExtensions, manifests);

        yield* Effect.logInfo(
          `[Extension] System ready. Mounted: ${manifests.length}`,
        );
      }),

      executeWasm: (pluginId, funcName) =>
        Effect.gen(function* () {
          const reqId = crypto.randomUUID();

          yield* Effect.logDebug(
            `[Extension] Executing WASM: ${pluginId} -> ${funcName} (req_id: ${reqId})`,
          );

          const task = Effect.tryPromise({
            try: () =>
              invoke<any>("execute_extension_wasm", {
                reqId,
                pluginId,
                funcName,
              }),
            catch: parseExtensionError,
          });

          return yield* task.pipe(
            Effect.tap((res) =>
              Effect.logDebug(
                `[Extension] WASM Result for ${reqId}: ${JSON.stringify(res)}`,
              ),
            ),
            Effect.tapError((err) =>
              Effect.logError(
                `[Extension] WASM Execution failed: ${err.message}`,
              ),
            ),
            Effect.onInterrupt(() =>
              Effect.gen(function* () {
                yield* Effect.logWarning(
                  `[Extension] Interrupting WASM task: ${reqId}`,
                );
                yield* Effect.tryPromise({
                  try: () => invoke("cancel_extension_wasm", { reqId }),
                  catch: (e) => e,
                }).pipe(
                  Effect.catchAll((e) =>
                    Effect.logError(
                      `[Extension] Failed to send cancel signal to Rust: ${e}`,
                    ),
                  ),
                );
              }),
            ),
          );
        }),

      installExtension: (zipPath) =>
        Effect.gen(function* () {
          const manifest = yield* Effect.tryPromise({
            try: () =>
              invoke<ExtensionManifest>("install_extension", { zipPath }),
            catch: parseExtensionError,
          });

          yield* loadScript(manifest);

          yield* Ref.update(mountedExtensions, (prev) => {
            const filtered = prev.filter((m) => m.id !== manifest.id);
            return [...filtered, manifest];
          });

          return manifest;
        }),

      updateExtension: (pluginId, zipPath) =>
        Effect.gen(function* () {
          const manifest = yield* Effect.tryPromise({
            try: () =>
              invoke<ExtensionManifest>("update_extension", {
                pluginId,
                zipPath,
              }),
            catch: parseExtensionError,
          });

          yield* loadScript(manifest);

          yield* Ref.update(mountedExtensions, (prev) => {
            const filtered = prev.filter((m) => m.id !== manifest.id);
            return [...filtered, manifest];
          });

          return manifest;
        }),

      deleteExtension: (pluginId) =>
        Effect.gen(function* () {
          yield* Effect.tryPromise({
            try: () => invoke<void>("delete_extension", { pluginId }),
            catch: parseExtensionError,
          });

          yield* Ref.update(mountedExtensions, (prev) =>
            prev.filter((m) => m.id !== pluginId),
          );
        }),
    });
  }),
);
