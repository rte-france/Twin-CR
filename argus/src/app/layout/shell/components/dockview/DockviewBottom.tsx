/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { onMount, onCleanup, createSignal } from "solid-js";
import { render } from "solid-js/web";
import { DockviewComponent } from "dockview-core";
import { MfeLoader } from "../MfeLoader";
import {
  leftSidebarTools,
  rightSidebarTools,
} from "@/config/layouts/game-master";
import { LeftHeaderActions } from "./LeftHeaderActions";
import { DockviewTab } from "./DockviewTab";
import { useLayout } from "../../providers/LayoutProvider";

export const [activeBottomTools, setActiveBottomTools] = createSignal<string[]>(
  [],
);
export const DOCKVIEW_CMD_EVENT = "argus:dockview-cmd";
const DOCKVIEW_STATE_KEY = "argus-dockview-state";

export const DockviewBottom = () => {
  let containerRef!: HTMLDivElement;
  let dockview: DockviewComponent;
  const layout = useLayout();
  const allTools = [...leftSidebarTools, ...rightSidebarTools];

  const syncState = () => {
    const visibleIds = dockview.panels
      .filter((p) => p.api.isActive)
      .map((p) => p.id);
    setActiveBottomTools(visibleIds);
  };

  onMount(() => {
    dockview = new DockviewComponent(containerRef, {
      className: "dockview-theme-custom",
      defaultTabComponent: "default-tab",

      createComponent: (options) => {
        const manifest = allTools.find((p) => p.elementTag === options.name);
        const containerDiv = document.createElement("div");
        containerDiv.className = "w-full h-full";
        let disposeSolid: (() => void) | null = null;

        return {
          element: containerDiv,
          init: () => {
            if (manifest) {
              disposeSolid = render(
                () => <MfeLoader manifest={manifest} />,
                containerDiv,
              );
            }
          },
          dispose: () => {
            if (disposeSolid) disposeSolid();
          },
        };
      },

      createTabComponent: () => {
        const el = document.createElement("div");
        el.className = "w-full h-full";
        let disposeSolid: (() => void) | null = null;

        return {
          element: el,
          init: (params) => {
            disposeSolid = render(
              () => (
                <DockviewTab
                  api={params.api}
                  title={params.title}
                  params={params.params}
                />
              ),
              el,
            );
          },
          dispose: () => disposeSolid?.(),
        };
      },

      createLeftHeaderActionComponent: (group) => {
        const el = document.createElement("div");
        el.className = "h-full";
        let disposeSolid: (() => void) | null = null;

        return {
          element: el,
          init: () => {
            disposeSolid = render(
              () => <LeftHeaderActions group={group} />,
              el,
            );
          },
          dispose: () => disposeSolid?.(),
        };
      },
    });

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.clientWidth > 0 && containerRef.clientHeight > 0) {
        dockview.layout(containerRef.clientWidth, containerRef.clientHeight);
      }
    });
    resizeObserver.observe(containerRef);

    try {
      const savedState = localStorage.getItem(DOCKVIEW_STATE_KEY);
      if (savedState) dockview.fromJSON(JSON.parse(savedState));
    } catch (e) {}

    syncState();
    dockview.onDidActivePanelChange(syncState);
    dockview.onDidAddPanel(syncState);

    dockview.onDidRemovePanel(() => {
      syncState();
      if (dockview.panels.length === 0) {
        window.dispatchEvent(new CustomEvent("argus:bottom-empty"));
      }
    });

    dockview.onDidLayoutChange(() => {
      try {
        localStorage.setItem(
          DOCKVIEW_STATE_KEY,
          JSON.stringify(dockview.toJSON()),
        );
      } catch (e) {}
    });

    const handleCommand = (e: Event) => {
      const { action, id } = (e as CustomEvent).detail;

      if (action === "ADD") {
        const manifest = allTools.find((p) => p.id === id);
        if (!manifest) return;

        const existing = dockview.getGroupPanel(manifest.id);

        if (existing) {
          existing.api.setActive();
          return;
        }

        let targetPosition: any = undefined;

        if (dockview.activeGroup) {
          const activeGroup = dockview.activeGroup;
          const currentTab = activeGroup.activePanel;
          const insertIndex = currentTab
            ? activeGroup.panels.indexOf(currentTab) + 1
            : undefined;

          targetPosition = {
            referenceGroup: activeGroup,
            index: insertIndex,
          };
        }

        const newPanel = dockview.addPanel({
          id: manifest.id,
          component: manifest.elementTag,
          title: manifest.label,
          position: targetPosition,
        });

        newPanel.api.setActive();
      }
    };

    const handleFocusTool = (e: Event) => {
      const customEvent = e as CustomEvent;
      const id = customEvent.detail;
      const panel = dockview.getPanel(id);

      if (panel) {
        customEvent.preventDefault();

        if (!layout.isOpen("bottom")) {
          if (layout.state.bottom.size < 100) {
            layout.setDim("bottom", 250);
          }
          layout.toggle("bottom");
        }

        layout.setActiveId("bottom", "open");
        panel.api.setActive();
      }
    };

    const onMovePanel = ((e: Event) => {
      const { id, target, manifest } = (e as CustomEvent).detail;
      const existingPanel = dockview.getGroupPanel(id);

      if (target === "bottom") {
        if (!existingPanel) {
          const newPanel = dockview.addPanel({
            id: manifest.id,
            component: manifest.elementTag,
            title: manifest.label,
            params: manifest,
          });
          newPanel.api.setActive();
        } else {
          existingPanel.api.setActive();
        }
      } else {
        if (existingPanel) {
          dockview.removePanel(existingPanel);
        }
      }
    }) as EventListener;

    window.addEventListener("argus:move-panel", onMovePanel);
    window.addEventListener(DOCKVIEW_CMD_EVENT, handleCommand);
    window.addEventListener("argus:focus-tool", handleFocusTool);

    dockview.onUnhandledDragOverEvent((e) => {
      if (e.nativeEvent.dataTransfer?.types.includes("argus/tool-id"))
        e.accept();
    });

    dockview.onDidDrop((e) => {
      const toolId = e.nativeEvent.dataTransfer?.getData("argus/tool-id");
      if (toolId) {
        const manifest = allTools.find((t) => t.id === toolId);
        if (manifest) {
          const existing = dockview.getGroupPanel(manifest.id);
          if (existing && e.group && existing.group) {
            dockview.moveGroupOrPanel({
              from: { groupId: existing.group.id, panelId: existing.id },
              to: { group: e.group, position: e.position },
            });
            existing.api.setActive();
          } else {
            dockview.addPanel({
              id: manifest.id,
              component: manifest.elementTag,
              title: manifest.label,
              position: e.group
                ? {
                    referenceGroup: e.group,
                    direction:
                      e.position !== "center" ? (e.position as any) : undefined,
                  }
                : undefined,
            });
          }
        }
      }
    });

    onCleanup(() => {
      resizeObserver.disconnect();
      window.removeEventListener("argus:move-panel", onMovePanel);
      window.removeEventListener(DOCKVIEW_CMD_EVENT, handleCommand);
      window.removeEventListener("argus:focus-tool", handleFocusTool);
      dockview.dispose();
    });
  });

  return (
    <div
      ref={containerRef}
      class="w-full h-full bg-pre-bg dockview-theme-custom"
    />
  );
};
