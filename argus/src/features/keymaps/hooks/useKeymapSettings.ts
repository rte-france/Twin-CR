/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount } from "solid-js";
import { Effect } from "effect";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { KeymapStore, Keymaps } from "@/services/keymaps";
import type { CommandDefinition, KeymapConfig } from "@/types/keymap.type";

export function useKeymapSettings() {
  const [commands, setCommands] = createSignal<readonly CommandDefinition[]>(
    [],
  );
  const [config, setConfig] = createSignal<KeymapConfig>({});
  const [savingId, setSavingId] = createSignal<string | null>(null);
  const [error, setError] = createSignal<string | null>(null);

  const loadData = async () => {
    try {
      const { allCmds, cfg } = await getSystemRuntime().runPromise(
        Effect.gen(function* () {
          const store = yield* KeymapStore;
          const allCmds = yield* store.getAllCommands;
          const cfg = yield* store.getConfig;
          return { allCmds, cfg };
        }),
      );
      setCommands(allCmds);
      setConfig(cfg);
      setError(null);
    } catch (err) {
      setError(String(err));
    }
  };

  const updateBinding = async (
    context: string,
    commandId: string,
    newKey: string,
  ) => {
    setSavingId(commandId);
    try {
      const updatedConfig = await getSystemRuntime().runPromise(
        Effect.gen(function* () {
          const store = yield* KeymapStore;
          yield* store.updateBinding(context, commandId, newKey);
          return yield* store.getConfig;
        }),
      );
      setConfig(updatedConfig);
      setSavingId(null);
    } catch (err) {
      setSavingId(null);
      setError(String(err));
      throw err;
    }
  };

  const getEventString = (event: KeyboardEvent): string => {
    return getSystemRuntime().runSync(
      Effect.gen(function* () {
        const utils = yield* Keymaps;
        return utils.getEventString(event, "logical");
      }),
    );
  };

  onMount(() => {
    loadData();
  });

  return {
    commands,
    config,
    savingId,
    error,
    loadData,
    updateBinding,
    getEventString,
  };
}
