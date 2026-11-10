/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Layer, Ref, Option, Runtime } from "effect";

import { flattenKeymaps } from "@/config/keymaps";
import type {
  CommandId,
  KeymapConfig,
  CommandDefinition,
} from "@/types/keymap.type";
import { getEventString, isInputElement } from "./utils";

export interface KeymapsService {
  readonly getEventString: (
    e: KeyboardEvent | MouseEvent,
    layoutMode?: "logical" | "physical",
  ) => string;
  readonly isInputElement: (target: HTMLElement) => boolean;
}

export class Keymaps extends Context.Tag("Keymaps")<
  Keymaps,
  KeymapsService
>() {}

export const KeymapsLive = Layer.succeed(
  Keymaps,
  Keymaps.of({
    getEventString: (e, layoutMode) => getEventString(e, layoutMode),
    isInputElement: (target) => isInputElement(target),
  }),
);

export interface KeymapStoreService {
  readonly getConfig: Effect.Effect<KeymapConfig>;
  readonly updateBinding: (
    context: string,
    commandId: CommandId,
    newKey: string,
  ) => Effect.Effect<void>;
  readonly getCommand: (
    id: CommandId,
  ) => Effect.Effect<Option.Option<CommandDefinition>>;
  readonly registerCommands: (
    commands: readonly CommandDefinition[],
  ) => Effect.Effect<void>;
  readonly getAllCommands: Effect.Effect<readonly CommandDefinition[]>;
}

export class KeymapStore extends Context.Tag("KeymapStore")<
  KeymapStore,
  KeymapStoreService
>() {}

export const KeymapStoreLive = Layer.effect(
  KeymapStore,
  Effect.gen(function* () {
    const defaultCommands = flattenKeymaps();
    const initialMap = new Map<CommandId, CommandDefinition>(
      defaultCommands.map((c) => [c.id, c]),
    );
    const commandsRef = yield* Ref.make(initialMap);

    const defaultConfig: KeymapConfig = {
      Global: defaultCommands.flatMap((cmd) =>
        cmd.defaultKeys.map((key) => ({
          commandId: cmd.id,
          keyCombination: key,
        })),
      ),
    };
    const configRef = yield* Ref.make(defaultConfig);

    yield* Effect.logDebug("[KeymapStore] Store initialized");

    return KeymapStore.of({
      getConfig: Ref.get(configRef),
      getCommand: (id) =>
        Effect.map(Ref.get(commandsRef), (map) =>
          Option.fromNullable(map.get(id)),
        ),
      registerCommands: (commands) =>
        Ref.update(commandsRef, (currentMap) => {
          const nextMap = new Map(currentMap);
          commands.forEach((cmd) => nextMap.set(cmd.id, cmd));
          return nextMap;
        }),
      updateBinding: (context, commandId, newKey) =>
        Ref.update(configRef, (currentConfig) => {
          const contextBindings = currentConfig[context] || [];
          const filtered = contextBindings.filter(
            (b) => b.commandId !== commandId && b.keyCombination !== newKey,
          );
          return {
            ...currentConfig,
            [context]: [...filtered, { commandId, keyCombination: newKey }],
          };
        }),
      getAllCommands: Effect.map(Ref.get(commandsRef), (map) =>
        Array.from(map.values()),
      ),
    });
  }),
);

export interface KeymapEngineService {
  readonly setContext: (context: string) => Effect.Effect<void>;
  readonly setEnabled: (enabled: boolean) => Effect.Effect<void>;
  readonly setLayoutMode: (mode: "logical" | "physical") => Effect.Effect<void>;
}

export class KeymapEngine extends Context.Tag("KeymapEngine")<
  KeymapEngine,
  KeymapEngineService
>() {}

export const KeymapEngineLive = Layer.scoped(
  KeymapEngine,
  Effect.gen(function* () {
    const store = yield* KeymapStore;
    const utils = yield* Keymaps;
    const runtime = yield* Effect.runtime<never>();

    const activeContextRef = yield* Ref.make<string>("Global");
    const isEnabledRef = yield* Ref.make<boolean>(true);
    const layoutModeRef = yield* Ref.make<"logical" | "physical">("logical");

    const lastShiftTimeRef = yield* Ref.make<number>(0);
    const sequenceBufferRef = yield* Ref.make<string[]>([]);
    const bufferTimeoutRef = yield* Ref.make<number | undefined>(undefined);

    const clearSequenceBuffer = Effect.gen(function* () {
      yield* Ref.set(sequenceBufferRef, []);
      window.dispatchEvent(new CustomEvent("keymap:sequence-cleared"));
    });

    const executeCommand = (commandId: CommandId) =>
      Effect.gen(function* () {
        const maybeCommand = yield* store.getCommand(commandId);
        if (Option.isSome(maybeCommand)) {
          yield* Effect.tryPromise(async () => {
            await maybeCommand.value.handler();
          }).pipe(
            Effect.catchAllCause((cause) =>
              Effect.logError("[KeymapEngine] Execution error:", cause),
            ),
          );
        } else {
          Effect.logWarning(`[KeymapEngine] Command not found: "${commandId}"`);
        }
      });

    const handleInput = (event: KeyboardEvent | MouseEvent) =>
      Effect.gen(function* () {
        const isEnabled = yield* Ref.get(isEnabledRef);
        const isRepeat = event instanceof KeyboardEvent && event.repeat;

        if (
          !isEnabled ||
          isRepeat ||
          utils.isInputElement(event.target as HTMLElement)
        )
          return;

        const currentLayoutMode = yield* Ref.get(layoutModeRef);
        let pressedKeyStr = utils.getEventString(event, currentLayoutMode);

        if (!pressedKeyStr) return;

        const isModifierOnly = [
          "control",
          "meta",
          "shift",
          "alt",
          "mod",
          "ctrl",
        ].includes(pressedKeyStr);

        if (event instanceof KeyboardEvent && event.key === "Shift") {
          const now = Date.now();
          const lastTime = yield* Ref.get(lastShiftTimeRef);
          if (now - lastTime < 300) {
            pressedKeyStr = "shift+shift";
            yield* Ref.set(lastShiftTimeRef, 0);
          } else {
            yield* Ref.set(lastShiftTimeRef, now);
            return;
          }
        } else if (isModifierOnly) {
          return;
        }

        const currentBuffer = yield* Ref.get(sequenceBufferRef);
        const newSequence = [...currentBuffer, pressedKeyStr];
        const sequenceString = newSequence.join(" ");

        const currentContext = yield* Ref.get(activeContextRef);
        const config = yield* store.getConfig;

        const bindingsToSearch = [
          ...(config[currentContext] || []),
          ...(config["Global"] || []),
        ];

        const exactMatch = bindingsToSearch.find(
          (b) => b.keyCombination.toLowerCase() === sequenceString,
        );
        const isPartialMatch = bindingsToSearch.some((b) =>
          b.keyCombination.toLowerCase().startsWith(sequenceString + " "),
        );

        if (isPartialMatch) {
          event.preventDefault();
          yield* Ref.set(sequenceBufferRef, newSequence);

          window.dispatchEvent(
            new CustomEvent("keymap:sequence-pending", {
              detail: { sequence: sequenceString },
            }),
          );

          const currentTimeout = yield* Ref.get(bufferTimeoutRef);
          if (currentTimeout) clearTimeout(currentTimeout);

          const newTimeout = window.setTimeout(() => {
            if (exactMatch) {
              Runtime.runFork(runtime)(
                Effect.gen(function* () {
                  yield* executeCommand(exactMatch.commandId);
                  yield* clearSequenceBuffer;
                }),
              );
            } else {
              Runtime.runFork(runtime)(clearSequenceBuffer);
            }
          }, 400);

          yield* Ref.set(bufferTimeoutRef, newTimeout);
          return;
        }

        if (exactMatch) {
          event.preventDefault();
          yield* clearSequenceBuffer;
          yield* executeCommand(exactMatch.commandId);
          return;
        }

        yield* clearSequenceBuffer;
      });

    const runFork = (event: KeyboardEvent | MouseEvent) => {
      Runtime.runFork(runtime)(handleInput(event));
    };

    const handleBlur = () => {
      Runtime.runFork(runtime)(clearSequenceBuffer);
    };

    // Guard against multiple runtime instances attaching redundant listeners to the same window
    yield* Effect.acquireRelease(
      Effect.sync(() => {
        const win = window as any;
        if (!win.__KEYMAP_ATTACHED_LISTENERS__) {
          win.__KEYMAP_ATTACHED_LISTENERS__ = new Set();
        }
        win.__KEYMAP_ATTACHED_LISTENERS__.add(runFork);

        if (win.__KEYMAP_ATTACHED_LISTENERS__.size === 1) {
          win.addEventListener("keydown", (e: KeyboardEvent) => {
            const firstListener = win.__KEYMAP_ATTACHED_LISTENERS__
              ?.values()
              .next().value;
            firstListener?.(e);
          });
          win.addEventListener("mousedown", (e: MouseEvent) => {
            const firstListener = win.__KEYMAP_ATTACHED_LISTENERS__
              ?.values()
              .next().value;
            firstListener?.(e);
          });
          win.addEventListener("blur", handleBlur);
        }
      }),
      () =>
        Effect.sync(() => {
          const win = window as any;
          win.__KEYMAP_ATTACHED_LISTENERS__?.delete(runFork);
        }),
    );

    return KeymapEngine.of({
      setContext: (context) => Ref.set(activeContextRef, context),
      setEnabled: (enabled) => Ref.set(isEnabledRef, enabled),
      setLayoutMode: (mode) => Ref.set(layoutModeRef, mode),
    });
  }),
);

export const KeymapSystemLive = Layer.mergeAll(
  KeymapsLive,
  KeymapStoreLive,
  KeymapEngineLive,
).pipe(Layer.provide(KeymapStoreLive), Layer.provide(KeymapsLive));
