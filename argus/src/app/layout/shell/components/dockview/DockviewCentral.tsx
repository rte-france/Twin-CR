/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount, onCleanup } from "solid-js";
import { render } from "solid-js/web";
import { DockviewComponent } from "dockview-core";
import { MfeLoader } from "../MfeLoader";
import { type OpenCentralParams } from "@/utils/openInCentral";
import { DockviewTab } from "./DockviewTab";
import { LeftHeaderActions } from "./LeftHeaderActions";
import { usePlacement } from "../../providers/PlacementProvider";
import { RightHeaderActions } from "./RightHeaderActions";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { PanelManifest } from "@/types";
import { Watermark } from "./Watermark";

const CENTRAL_STATE_KEY = "argus-central-dockview-state";

export const DockviewCentral = () => {
  let containerRef!: HTMLDivElement;
  let dockview: DockviewComponent;
  const { placement } = usePlacement();

  onMount(() => {
    dockview = new DockviewComponent(containerRef, {
      className: "dockview-theme-custom",
      defaultTabComponent: "default-tab",

      createWatermarkComponent: () => {
        const el = document.createElement("div");
        el.className = "h-full w-full";
        let disposeSolid: (() => void) | null = null;

        return {
          element: el,
          init: (params) => {
            disposeSolid = render(() => <Watermark {...params} />, el);
          },
          dispose: () => disposeSolid?.(),
        };
      },

      createComponent: () => {
        const containerDiv = document.createElement("div");
        containerDiv.className = "w-full h-full";
        let disposeSolid: (() => void) | null = null;
        const [componentProps, setComponentProps] = createSignal<unknown>();

        return {
          element: containerDiv,
          init: (parameters) => {
            const payload = parameters.params as OpenCentralParams;
            if (payload) {
              const manifest: PanelManifest = {
                id: payload.id,
                label: payload.title,
                iconId: payload.iconId ?? "lucide:file",
                elementTag: payload.elementTag,
                entryUrl: payload.entryUrl,
                isLocalFile: payload.isLocalFile,
              };
              setComponentProps(payload.params);

              disposeSolid = render(
                () => (
                  <MfeLoader
                    manifest={manifest}
                    componentProps={componentProps()}
                  />
                ),
                containerDiv,
              );
            }
          },
          // Reopening an already open panel updates its parameters instead of creating a new one
          update: (event) => {
            const payload = event.params as OpenCentralParams | undefined;
            if (payload?.params) setComponentProps(payload.params);
          },
          dispose: () => disposeSolid?.(),
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

      createRightHeaderActionComponent: (group) => {
        const el = document.createElement("div");
        el.className = "h-full";
        let disposeSolid: (() => void) | null = null;

        return {
          element: el,
          init: () => {
            disposeSolid = render(
              () => (
                <RightHeaderActions
                  group={group}
                  getDockview={() => dockview}
                />
              ),
              el,
            );
          },
          dispose: () => disposeSolid?.(),
        };
      },
    });

    dockview.onDidMaximizedGroupChange(() => {
      dockview.groups.forEach((group) => {
        if (group.api.isMaximized()) {
          group.element.classList.add("is-maximized-zoom");
        } else {
          group.element.classList.remove("is-maximized-zoom");
        }
      });
    });

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.clientWidth > 0 && containerRef.clientHeight > 0) {
        dockview.layout(containerRef.clientWidth, containerRef.clientHeight);
      }
    });
    resizeObserver.observe(containerRef);

    try {
      const savedState = localStorage.getItem(CENTRAL_STATE_KEY);
      if (savedState) dockview.fromJSON(JSON.parse(savedState));
    } catch (e) {}

    dockview.onDidLayoutChange(() => {
      try {
        localStorage.setItem(
          CENTRAL_STATE_KEY,
          JSON.stringify(dockview.toJSON()),
        );
      } catch (e) {}
    });

    const handleAdd = (e: Event) => {
      const payload = (e as CustomEvent<OpenCentralParams>).detail;

      const existing = dockview.getGroupPanel(payload.id);
      if (existing) {
        existing.update({ params: payload });
        existing.api.setTitle(payload.title);
        existing.api.setActive();
        return;
      }

      let targetPosition: any = undefined;
      const currentMode = placement();

      if (dockview.activeGroup) {
        const activeGroup = dockview.activeGroup;
        const currentTab = activeGroup.activePanel;
        const insertIndex = currentTab
          ? activeGroup.panels.indexOf(currentTab) + 1
          : undefined;
        targetPosition = {
          referenceGroup: activeGroup,
          index: insertIndex,
          direction: currentMode,
        };
      }

      const newPanel = dockview.addPanel({
        id: payload.id,
        component: payload.elementTag,
        title: payload.title,
        params: payload,
        position: targetPosition,
      });

      newPanel.api.setActive();
    };

    const handleFocusTool = (e: Event) => {
      const customEvent = e as CustomEvent;
      const panel = dockview.getPanel(customEvent.detail);

      if (panel) {
        customEvent.preventDefault();
        panel.api.setActive();
      }
    };

    const onMovePanel = ((e: Event) => {
      const { id, target, manifest } = (e as CustomEvent).detail;
      const existingPanel = dockview.getGroupPanel(id);

      if (target === "central") {
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

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "m") {
        e.preventDefault();

        const activeGroup = dockview.activeGroup;

        if (activeGroup) {
          if (activeGroup.api.isMaximized()) {
            activeGroup.api.exitMaximized();
          } else {
            activeGroup.api.maximize();
          }
        }
      }
    };

    const unlistenReattachPromise = getCurrentWindow().listen(
      "argus:reattach-panel",
      (event: any) => {
        window.dispatchEvent(
          new CustomEvent("argus:add-central", { detail: event.payload }),
        );
      },
    );

    window.addEventListener("argus:move-panel", onMovePanel);
    window.addEventListener("argus:add-central", handleAdd);
    window.addEventListener("argus:focus-tool", handleFocusTool);
    window.addEventListener("keydown", handleKeyDown);

    onCleanup(() => {
      resizeObserver.disconnect();
      window.removeEventListener("argus:move-panel", onMovePanel);
      window.removeEventListener("argus:add-central", handleAdd);
      window.removeEventListener("argus:focus-tool", handleFocusTool);
      window.removeEventListener("keydown", handleKeyDown);
      unlistenReattachPromise.then((unlisten) => unlisten());
      dockview.dispose();
    });
  });

  return (
    <div ref={containerRef} class="w-full h-full bg-bg dockview-theme-custom" />
  );
};
