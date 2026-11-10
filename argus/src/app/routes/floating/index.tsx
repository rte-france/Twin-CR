/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { useParams, useSearchParams } from "@solidjs/router";
import { createSignal, onMount, onCleanup } from "solid-js";
import { MfeLoader } from "@/app/layout/shell/components/MfeLoader";
import { hydratePanelFromUrlAndStorage } from "./panelHydration";

import { emit } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";

export const Floating = (props: { parentLabel: string }) => {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const [manifest, setManifest] = createSignal<any>(null);
  const [componentProps, setComponentProps] = createSignal<any>(null);
  const [originGroupId, setOriginGroupId] = createSignal<string | undefined>(
    (searchParams as Record<string, string | undefined>).groupId,
  );

  onMount(() => {
    const rawId = params.id || "";
    const hydrated = hydratePanelFromUrlAndStorage(
      rawId,
      searchParams as Record<string, string | undefined>,
      params.viewType,
    );

    setManifest(hydrated.manifest);
    setComponentProps(hydrated.componentProps);

    const windowContext = getCurrentWindow();
    let isClosing = false;

    const unlistenPromise = windowContext.onCloseRequested(async (event) => {
      if (isClosing) return;
      isClosing = true;
      event.preventDefault();

      try {
        const currentManifest = manifest();

        if (currentManifest) {
          const payload = {
            id: currentManifest.id,
            title: currentManifest.label,
            elementTag: currentManifest.elementTag,
            entryUrl: currentManifest.entryUrl,
            isLocalFile: currentManifest.isLocalFile,
            params: componentProps(),
            groupId: originGroupId(),
          };

          await emit("argus:reattach-panel", payload);
        }
      } catch (err) {
        console.error("Failed to emit reattach event:", err);
      } finally {
        await windowContext.destroy();
      }
    });

    onCleanup(() => {
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {});
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
