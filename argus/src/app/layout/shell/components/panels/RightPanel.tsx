/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
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
import { ADD_BOTTOM_RIGHT_EVENT } from "@/utils/openInCentral";
import { activeBottomRightId } from "../../utils";

export const RightPanel = () => {
  const layout = useLayout();
  const [mode] = useAppMode();

  const [activeTopId, setActiveTopId] = createSignal<string | null>(null);
  const [activeBottomId, setActiveBottomId] = createSignal<string | null>(null);

  const config = () => layoutConfigs[mode()];
  const panels = () => config().rightSidebarPanels || [];
  const tools = () => config().rightSidebarTools || [];

  createEffect(
    on(mode, (currentMode) => {
      const topSaved = localStorage.getItem(`argus-right-top-${currentMode}`);
      const bottomSaved = localStorage.getItem(
        `argus-right-bottom-${currentMode}`,
      );
      const toolSaved = localStorage.getItem(
        `argus-right-bottom-tool-${currentMode}`,
      );

      if (topSaved) setActiveTopId(topSaved);
      if (bottomSaved) setActiveBottomId(bottomSaved);

      if ((topSaved || bottomSaved) && !layout.isOpen("right")) {
        layout.toggle("right");
      }

      if (toolSaved) {
        const tool = tools().find((t) => t.id === toolSaved);
        if (tool && activeBottomRightId() !== tool.id) {
          window.dispatchEvent(
            new CustomEvent(ADD_BOTTOM_RIGHT_EVENT, {
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
          (t) => t.id === activeBottomRightId(),
        );
        if (activeBottomRightId() && !currentOpenInThisMode) {
          window.dispatchEvent(
            new CustomEvent("argus:toggle-right-bottom-panel"),
          );
        }
      }
    }),
  );

  createEffect(() => {
    activeTopId()
      ? localStorage.setItem(`argus-right-top-${mode()}`, activeTopId()!)
      : localStorage.removeItem(`argus-right-top-${mode()}`);
    activeBottomId()
      ? localStorage.setItem(`argus-right-bottom-${mode()}`, activeBottomId()!)
      : localStorage.removeItem(`argus-right-bottom-${mode()}`);

    activeBottomRightId()
      ? localStorage.setItem(
          `argus-right-bottom-tool-${mode()}`,
          activeBottomRightId()!,
        )
      : localStorage.removeItem(`argus-right-bottom-tool-${mode()}`);
  });

  createEffect(() => {
    if (activeBottomRightId() && !layout.isOpen("bottom")) {
      layout.toggle("bottom");
    }
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

    const handleKeyboardToggle = () => {
      if (!layout.isOpen("right")) {
        if (!activeTopId() && !activeBottomId()) {
          const firstPanel = panels().find(
            (m) => (m.position || "top") === "top",
          );
          if (firstPanel) setActiveTopId(firstPanel.id);
        }
        layout.toggle("right");
      } else {
        layout.toggle("right");
      }
    };

    window.addEventListener("argus:toggle-tool", handleToggle);
    window.addEventListener("argus:remove-panel", handleRemove);
    window.addEventListener("argus:toggle-right-panel", handleKeyboardToggle);

    onCleanup(() => {
      window.removeEventListener("argus:toggle-tool", handleToggle);
      window.removeEventListener("argus:remove-panel", handleRemove);
      window.removeEventListener(
        "argus:toggle-right-panel",
        handleKeyboardToggle,
      );
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
          <Separator class="w-6 mx-auto my-2 h-px bg-divider opacity-50 shrink-0" />
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
                isActive={activeBottomRightId() === tool.id}
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
