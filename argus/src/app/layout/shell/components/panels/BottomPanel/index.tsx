/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, onMount, onCleanup, Show } from "solid-js";
import {
  type OpenCentralParams,
  ADD_BOTTOM_LEFT_EVENT,
  ADD_BOTTOM_RIGHT_EVENT,
} from "@/utils/openInCentral";
import {
  activeBottomLeftId,
  activeBottomRightId,
  isLeftOpen,
  isRightOpen,
  PanelState,
  setActiveBottomLeftId,
  setActiveBottomRightId,
  setIsLeftOpen,
  setIsRightOpen,
} from "./utils";
import { PanelView } from "./PanelView";
import { Resizer } from "./Resizer";

export {
  activeBottomLeftId,
  activeBottomRightId,
  hasVisibleBottomPanels,
} from "./utils";

export const BottomPanel = () => {
  const loadSavedPanel = (key: string): PanelState | null => {
    const saved = localStorage.getItem(key);
    return saved ? JSON.parse(saved) : null;
  };

  const initialLeftData = loadSavedPanel("argus-bottom-left-data");
  const initialRightData = loadSavedPanel("argus-bottom-right-data");

  const [leftData, setLeftData] = createSignal<PanelState | null>(
    initialLeftData,
  );
  const [rightData, setRightData] = createSignal<PanelState | null>(
    initialRightData,
  );

  if (initialLeftData) {
    setActiveBottomLeftId(initialLeftData.manifest.id);
    const wasLeftOpen = localStorage.getItem("argus-bottom-left-open");
    setIsLeftOpen(wasLeftOpen === "false" ? false : true);
  }

  if (initialRightData) {
    setActiveBottomRightId(initialRightData.manifest.id);
    const wasRightOpen = localStorage.getItem("argus-bottom-right-open");
    setIsRightOpen(wasRightOpen === "false" ? false : true);
  }

  const savedWidth = localStorage.getItem("bottom_panel_left_width");
  const [leftWidth, setLeftWidth] = createSignal(
    savedWidth ? parseFloat(savedWidth) : 35,
  );

  let containerRef!: HTMLDivElement;

  const updateLeftWidth = (newWidth: number) => {
    setLeftWidth(newWidth);
    localStorage.setItem("bottom_panel_left_width", newWidth.toString());
  };

  createEffect(() => {
    const lData = leftData();
    if (lData) {
      localStorage.setItem("argus-bottom-left-data", JSON.stringify(lData));
    } else {
      localStorage.removeItem("argus-bottom-left-data");
    }
    localStorage.setItem(
      "argus-bottom-left-open",
      isLeftOpen() ? "true" : "false",
    );
  });

  createEffect(() => {
    const rData = rightData();
    if (rData) {
      localStorage.setItem("argus-bottom-right-data", JSON.stringify(rData));
    } else {
      localStorage.removeItem("argus-bottom-right-data");
    }
    localStorage.setItem(
      "argus-bottom-right-open",
      isRightOpen() ? "true" : "false",
    );
  });

  const handleOpen = (
    e: Event,
    activeId: string | null,
    isOpen: boolean,
    setIsOpen: (v: boolean) => void,
    setData: (d: PanelState) => void,
    setActiveId: (id: string) => void,
  ) => {
    const payload = (e as CustomEvent<OpenCentralParams>).detail;

    if (activeId === payload.id && isOpen) {
      setIsOpen(false);
    } else {
      setData({
        manifest: {
          id: payload.id,
          label: payload.title,
          iconId: payload.iconId ?? "lucide:file",
          elementTag: payload.elementTag,
          entryUrl: payload.entryUrl,
          isLocalFile: payload.isLocalFile,
        },
        params: payload.params,
      });
      setIsOpen(true);
      setActiveId(payload.id);
    }
  };

  onMount(() => {
    const onOpenLeft = (e: Event) =>
      handleOpen(
        e,
        activeBottomLeftId(),
        isLeftOpen(),
        setIsLeftOpen,
        setLeftData,
        setActiveBottomLeftId,
      );
    const onOpenRight = (e: Event) =>
      handleOpen(
        e,
        activeBottomRightId(),
        isRightOpen(),
        setIsRightOpen,
        setRightData,
        setActiveBottomRightId,
      );

    window.addEventListener(ADD_BOTTOM_LEFT_EVENT, onOpenLeft);
    window.addEventListener(ADD_BOTTOM_RIGHT_EVENT, onOpenRight);

    onCleanup(() => {
      window.removeEventListener(ADD_BOTTOM_LEFT_EVENT, onOpenLeft);
      window.removeEventListener(ADD_BOTTOM_RIGHT_EVENT, onOpenRight);
    });
  });

  return (
    <div
      ref={containerRef}
      class="flex w-full h-full bg-bg border-border overflow-hidden"
    >
      <Show when={isLeftOpen() && leftData()}>
        {(panel) => (
          <PanelView
            panel={panel()}
            style={{
              width: isRightOpen() && rightData() ? `${leftWidth()}%` : "100%",
              "flex-shrink": 0,
            }}
            onClose={() => setIsLeftOpen(false)}
          />
        )}
      </Show>

      <Show when={isLeftOpen() && leftData() && isRightOpen() && rightData()}>
        <Resizer
          getContainerRef={() => containerRef}
          onWidthChange={updateLeftWidth}
        />
      </Show>

      <Show when={isRightOpen() && rightData()}>
        {(panel) => (
          <PanelView
            panel={panel()}
            class="flex-1"
            onClose={() => setIsRightOpen(false)}
          />
        )}
      </Show>
    </div>
  );
};
