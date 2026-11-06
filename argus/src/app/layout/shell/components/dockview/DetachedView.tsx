/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount } from "solid-js";
import { MfeLoader } from "../MfeLoader";

export const DetachedView = (props: { windowLabel: string }) => {
  const [payload, setPayload] = createSignal<any>(null);

  onMount(() => {
    const storedData = sessionStorage.getItem(
      `detached_payload_${props.windowLabel}`,
    );
    if (storedData) {
      setPayload(JSON.parse(storedData));
      sessionStorage.removeItem(`detached_payload_${props.windowLabel}`);
    }
  });

  return (
    <div class="w-screen h-screen bg-bg text-fg overflow-hidden">
      {payload() ? (
        <MfeLoader
          manifest={payload().manifest || payload()}
          componentProps={payload().params}
        />
      ) : (
        <div class="flex items-center justify-center h-full">
          Chargement de l'outil...
        </div>
      )}
    </div>
  );
};
