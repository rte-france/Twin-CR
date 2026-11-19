/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onCleanup, onMount } from "solid-js";
import { Effect } from "effect";
import { listen } from "@tauri-apps/api/event";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { Settings as SettingsServiceTag } from "@/services/settings";
import type { SettingsType } from "@/services/settings";

export function useSettings() {
  const [settings, setSettings] = createSignal<SettingsType>({} as SettingsType);
  const [loading, setLoading] = createSignal(true);
  const [savingKey, setSavingKey] = createSignal<string | null>(null);
  const [error, setError] = createSignal<string | null>(null);

  onMount(() => {
    let unlistenFn: (() => void) | undefined;
    listen<SettingsType>("settings-changed", (event) => {
      setSettings(event.payload);
    }).then((fn) => {
      unlistenFn = fn;
    });

    onCleanup(() => {
      unlistenFn?.();
    });
  });

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSystemRuntime().runPromise(
        Effect.gen(function* () {
          const service = yield* SettingsServiceTag;
          return yield* service.loadSettings;
        }),
      );
      setSettings(data);
    } catch (err: any) {
      console.error("[useSettings] Failed to load settings:", err);
      setError(err?.message || "Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  const updateSettingPath = async (path: string[], value: any) => {
    const keyPath = path.join(".");
    try {
      setSavingKey(keyPath);
      setError(null);

      // Build nested patch object: ['network', 'proxy'] -> { network: { proxy: value } }
      const patch: Record<string, any> = {};
      let current = patch;
      for (let i = 0; i < path.length - 1; i++) {
        current[path[i]] = {};
        current = current[path[i]];
      }
      current[path[path.length - 1]] = value;

      const updated = await getSystemRuntime().runPromise(
        Effect.gen(function* () {
          const service = yield* SettingsServiceTag;
          return yield* service.patchSettings(patch);
        }),
      );
      setSettings(updated);
    } catch (err: any) {
      console.error(`[useSettings] Failed to update ${keyPath}:`, err);
      setError(err?.message || `Failed to update ${keyPath}`);
      throw err;
    } finally {
      setSavingKey(null);
    }
  };

  return {
    settings,
    loading,
    savingKey,
    error,
    loadSettings,
    updateSettingPath,
  };
}
