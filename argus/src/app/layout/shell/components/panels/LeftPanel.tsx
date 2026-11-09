/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createEffect,
  createSignal,
  For,
  onCleanup,
  onMount,
  on,
} from "solid-js";
import { useLayout } from "../../providers/LayoutProvider";
import { useAppMode } from "@/hooks/useAppMode";
import { layoutConfigs } from "@/config/layouts";
import { ActivityBar } from "../sidebars/ActivityBar";
import { Sidebar } from "../sidebars/Sidebar";
import { IconResolver } from "../IconResolver";
import { Separator } from "@kobalte/core/separator";
import { activeBottomLeftId } from "./BottomPanel";
import { ADD_BOTTOM_LEFT_EVENT } from "@/utils/openInCentral";

export const LeftPanel = () => {
  const layout = useLayout();
  const [mode] = useAppMode();

  const [activeTopId, setActiveTopId] = createSignal<string | null>(null);
  const [activeBottomId, setActiveBottomId] = createSignal<string | null>(null);

  const config = () => layoutConfigs[mode()];
  const panels = () => config().leftSidebarPanels || [];
  const tools = () => config().leftSidebarTools || [];

  createEffect(
    on(mode, (currentMode) => {
      const topSaved = localStorage.getItem(`argus-left-top-${currentMode}`);
      const bottomSaved = localStorage.getItem(
        `argus-left-bottom-${currentMode}`,
      );
      const toolSaved = localStorage.getItem(
        `argus-left-bottom-tool-${currentMode}`,
      );

      if (topSaved) setActiveTopId(topSaved);
      if (bottomSaved) setActiveBottomId(bottomSaved);

      if ((topSaved || bottomSaved) && !layout.isOpen("left")) {
        layout.toggle("left");
      }

      if (toolSaved) {
        const tool = tools().find((t) => t.id === toolSaved);
        if (tool && activeBottomLeftId() !== tool.id) {
          window.dispatchEvent(
            new CustomEvent(ADD_BOTTOM_LEFT_EVENT, {
              detail: {
                id: tool.id,
                title: tool.label || tool.id,
                iconId: tool.iconId,
                elementTag: tool.elementTag,
              },
            }),
          );
        }
      } else {
        const currentOpenInThisMode = tools().find(
          (t) => t.id === activeBottomLeftId(),
        );
        if (activeBottomLeftId() && !currentOpenInThisMode) {
          window.dispatchEvent(
            new CustomEvent("argus:toggle-left-bottom-panel"),
          );
        }
      }
    }),
  );

  createEffect(() => {
    activeTopId()
      ? localStorage.setItem(`argus-left-top-${mode()}`, activeTopId()!)
      : localStorage.removeItem(`argus-left-top-${mode()}`);

    activeBottomId()
      ? localStorage.setItem(`argus-left-bottom-${mode()}`, activeBottomId()!)
      : localStorage.removeItem(`argus-left-bottom-${mode()}`);

    activeBottomLeftId()
      ? localStorage.setItem(
          `argus-left-bottom-tool-${mode()}`,
          activeBottomLeftId()!,
        )
      : localStorage.removeItem(`argus-left-bottom-tool-${mode()}`);
  });

  createEffect(() => {
    if (activeBottomLeftId() && !layout.isOpen("bottom")) {
      layout.toggle("bottom");
    }
  });

  onMount(() => {
    const handleToggle = (e: Event) => {
      const { id, side } = (e as CustomEvent).detail;
      if (side !== "left") return;

      const manifest = panels().find((m) => m.id === id);
      if (!manifest) return;

      const position = manifest.position || "top";

      if (position === "top") {
        setActiveTopId((prev) => (prev === id ? null : id));
      } else {
        setActiveBottomId((prev) => (prev === id ? null : id));
      }

      if (!activeTopId() && !activeBottomId() && layout.isOpen("left")) {
        layout.toggle("left");
      } else if (
        (activeTopId() || activeBottomId()) &&
        !layout.isOpen("left")
      ) {
        layout.toggle("left");
      }
    };

    const handleRemove = (e: Event) => {
      const { id, side } = (e as CustomEvent).detail;
      if (side !== "left") return;

      if (activeTopId() === id) setActiveTopId(null);
      if (activeBottomId() === id) setActiveBottomId(null);

      if (!activeTopId() && !activeBottomId() && layout.isOpen("left")) {
        layout.toggle("left");
      }
    };

    const handleKeyboardToggle = () => {
      if (!layout.isOpen("left")) {
        if (!activeTopId() && !activeBottomId()) {
          const firstPanel = panels().find(
            (m) => (m.position || "top") === "top",
          );
          if (firstPanel) setActiveTopId(firstPanel.id);
        }
        layout.toggle("left");
      } else {
        layout.toggle("left");
      }
    };

    window.addEventListener("argus:toggle-tool", handleToggle);
    window.addEventListener("argus:remove-panel", handleRemove);
    window.addEventListener("argus:toggle-left-panel", handleKeyboardToggle);

    onCleanup(() => {
      window.removeEventListener("argus:toggle-tool", handleToggle);
      window.removeEventListener("argus:remove-panel", handleRemove);
      window.removeEventListener(
        "argus:toggle-left-panel",
        handleKeyboardToggle,
      );
    });
  });

  const topManifest = () => panels().find((m) => m.id === activeTopId());
  const bottomManifest = () => panels().find((m) => m.id === activeBottomId());

  return (
    <div class="flex h-full shrink-0">
      <div class="w-10 h-full flex flex-col justify-between border-r border-border bg-sidebar-bg shrink-0 z-10">
        <div class="flex flex-col">
          <For each={panels().filter((m) => (m.position || "top") === "top")}>
            {(panel) => (
              <ActivityBar
                id={panel.id}
                side="left"
                isActive={activeTopId() === panel.id}
                title={panel.label || panel.id}
                icon={<IconResolver name={panel.iconId} />}
              />
            )}
          </For>
          <Separator class="w-6 mx-auto my-2 h-px bg-divider opacity-50 shrink-0" />
          <For each={panels().filter((m) => m.position === "bottom")}>
            {(panel) => (
              <ActivityBar
                id={panel.id}
                side="left"
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
                side="left"
                target="bottom"
                isActive={activeBottomLeftId() === tool.id}
                title={tool.label || tool.id}
                elementTag={tool.elementTag || tool.id}
                icon={<IconResolver name={tool.iconId} />}
              />
            )}
          </For>
        </div>
      </div>

      <Sidebar
        side="left"
        topManifest={topManifest()}
        bottomManifest={bottomManifest()}
      />
    </div>
  );
};
