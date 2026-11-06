/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, createSignal, For, onCleanup, onMount } from "solid-js";
import { useLayout } from "../../providers/LayoutProvider";
import { useAppMode } from "@/hooks/useAppMode";
import { layoutConfigs } from "@/config/layouts";
import { ActivityBar } from "../sidebars/ActivityBar";
import { Sidebar } from "../sidebars/Sidebar";
import { IconResolver } from "../IconResolver";
import { Separator } from "@kobalte/core/separator";

export const RightPanel = () => {
  const layout = useLayout();
  const [mode] = useAppMode();

  const [activeTopId, setActiveTopId] = createSignal<string | null>(null);
  const [activeBottomId, setActiveBottomId] = createSignal<string | null>(null);

  const config = () => layoutConfigs[mode()];
  const panels = () => config().rightSidebarPanels || [];
  const tools = () => config().rightSidebarTools || [];

  createEffect(() => {
    const topSaved = localStorage.getItem(`argus-right-top-${mode()}`);
    const bottomSaved = localStorage.getItem(`argus-right-bottom-${mode()}`);

    if (topSaved) setActiveTopId(topSaved);
    if (bottomSaved) setActiveBottomId(bottomSaved);

    if ((topSaved || bottomSaved) && !layout.isOpen("right")) {
      layout.toggle("right");
    }
  });

  createEffect(() => {
    activeTopId()
      ? localStorage.setItem(`argus-right-top-${mode()}`, activeTopId()!)
      : localStorage.removeItem(`argus-right-top-${mode()}`);
    activeBottomId()
      ? localStorage.setItem(`argus-right-bottom-${mode()}`, activeBottomId()!)
      : localStorage.removeItem(`argus-right-bottom-${mode()}`);
  });

  onMount(() => {
    const handleToggle = (e: Event) => {
      const { id, side } = (e as CustomEvent).detail;
      if (side !== "right") return;

      const manifest = panels().find((m) => m.id === id);
      if (!manifest) return;

      const position = manifest.position || "top";

      if (position === "top") {
        setActiveTopId((prev) => (prev === id ? null : id));
      } else {
        setActiveBottomId((prev) => (prev === id ? null : id));
      }

      if (!activeTopId() && !activeBottomId() && layout.isOpen("right")) {
        layout.toggle("right");
      } else if (
        (activeTopId() || activeBottomId()) &&
        !layout.isOpen("right")
      ) {
        layout.toggle("right");
      }
    };

    const handleRemove = (e: Event) => {
      const { id, side } = (e as CustomEvent).detail;
      if (side !== "right") return;

      if (activeTopId() === id) setActiveTopId(null);
      if (activeBottomId() === id) setActiveBottomId(null);

      if (!activeTopId() && !activeBottomId() && layout.isOpen("right")) {
        layout.toggle("right");
      }
    };

    window.addEventListener("argus:toggle-tool", handleToggle);
    window.addEventListener("argus:remove-panel", handleRemove);

    onCleanup(() => {
      window.removeEventListener("argus:toggle-tool", handleToggle);
      window.removeEventListener("argus:remove-panel", handleRemove);
    });
  });

  const topManifest = () => panels().find((m) => m.id === activeTopId());
  const bottomManifest = () => panels().find((m) => m.id === activeBottomId());

  return (
    <div class="flex h-full shrink-0">
      <Sidebar
        side="right"
        topManifest={topManifest()}
        bottomManifest={bottomManifest()}
      />

      <div class="w-10 h-full flex flex-col justify-between border-l border-border bg-sidebar-bg shrink-0 z-10">
        <div class="flex flex-col">
          <For each={panels().filter((m) => (m.position || "top") === "top")}>
            {(panel) => (
              <ActivityBar
                id={panel.id}
                side="right"
                isActive={activeTopId() === panel.id}
                title={panel.label || panel.id}
                icon={<IconResolver name={panel.iconId} />}
              />
            )}
          </For>
          <Separator class="w-6 mx-auto my-2 h-px bg-border opacity-50 shrink-0" />
          <For each={panels().filter((m) => m.position === "bottom")}>
            {(panel) => (
              <ActivityBar
                id={panel.id}
                side="right"
                isActive={activeBottomId() === panel.id}
                title={panel.label || panel.id}
                icon={<IconResolver name={panel.iconId} />}
              />
            )}
          </For>
        </div>

        <div class="flex flex-col">
          <For each={tools()}>
            {(tool) => (
              <ActivityBar
                id={tool.id}
                side="right"
                target="bottom"
                isActive={false}
                title={tool.label || tool.id}
                elementTag={tool.elementTag || tool.id}
                icon={<IconResolver name={tool.iconId} />}
              />
            )}
          </For>
        </div>
      </div>
    </div>
  );
};
