/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { useParams } from "@solidjs/router";
import { createSignal, onMount, onCleanup } from "solid-js";
import { MfeLoader } from "@/app/layout/shell/components/MfeLoader";

import { emitTo } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";

export const Floating = (props: { parentLabel: string }) => {
  const params = useParams();
  const [manifest, setManifest] = createSignal<any>(null);
  const [componentProps, setComponentProps] = createSignal<any>(null);

  onMount(() => {
    const id = decodeURIComponent(params.id!!);
    const storageKey = `detached_payload_${id}`;
    const storedData = localStorage.getItem(storageKey);

    if (storedData) {
      const parsedData = JSON.parse(storedData);

      const reconstructedManifest = {
        id: parsedData.id || id,
        label: parsedData.label || parsedData.title,
        iconId: parsedData.iconId || "file",
        elementTag: parsedData.elementTag,
        entryUrl: parsedData.entryUrl,
        isLocalFile: parsedData.isLocalFile,
      };

      setManifest(reconstructedManifest);
      setComponentProps(parsedData.params || parsedData);

      localStorage.removeItem(storageKey);
    } else {
      console.warn("No payload found for l'ID :", id);

      if (params.viewType) {
        setManifest({
          id: id,
          elementTag: params.viewType,
        });
      }
    }

    const windowContext = getCurrentWindow();

    const unlistenPromise = windowContext.onCloseRequested(async (event) => {
      event.preventDefault();

      const currentManifest = manifest();

      if (currentManifest) {
        const payload = {
          id: currentManifest.id,
          title: currentManifest.label,
          elementTag: currentManifest.elementTag,
          entryUrl: currentManifest.entryUrl,
          isLocalFile: currentManifest.isLocalFile,
          params: componentProps(),
        };

        const targetLabel = props.parentLabel || "main";
        await emitTo(targetLabel, "argus:reattach-panel", payload);
      }

      const unlisten = await unlistenPromise;
      unlisten();

      await windowContext.close();
    });

    onCleanup(() => {
      unlistenPromise.then((unlisten) => unlisten());
    });
  });

  return (
    <div class="w-full h-full bg-bg text-fg relative">
      {manifest()?.elementTag ? (
        <MfeLoader manifest={manifest()} componentProps={componentProps()} />
      ) : (
        <div class="flex items-center justify-center h-full text-fg/50 text-sm animate-pulse">
          Loading {decodeURIComponent(params.id!!)}"...
        </div>
      )}
    </div>
  );
};
