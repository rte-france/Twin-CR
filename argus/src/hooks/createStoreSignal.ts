/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, type Signal, onCleanup } from "solid-js";

export function createStoredSignal<T>(key: string, initialValue: T): Signal<T> {
  const getInitial = (): T => {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : initialValue;
  };

  const [state, setState] = createSignal<T>(getInitial());

  createEffect(() => {
    localStorage.setItem(key, JSON.stringify(state()));
  });

  const handleStorageChange = (e: StorageEvent) => {
    if (e.key === key && e.newValue) {
      setState(JSON.parse(e.newValue));
    }
  };

  window.addEventListener("storage", handleStorageChange);

  onCleanup(() => {
    window.removeEventListener("storage", handleStorageChange);
  });

  return [state, setState];
}
