/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount, onCleanup, type Component } from "solid-js";
import { FiMaximize, FiMinimize, FiExternalLink } from "solid-icons/fi";
import type { DockviewGroupPanel, DockviewComponent } from "dockview-core";
import { Effect } from "effect";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { WindowBootstrapper } from "@/services/window-bootstrap";
import { buildPanelRoute } from "./panelUrlBuilder";

interface RightHeaderActionsProps {
  group: DockviewGroupPanel;
  getDockview: () => DockviewComponent;
}

export const RightHeaderActions: Component<RightHeaderActionsProps> = (
  props,
) => {
  const [isMaximized, setIsMaximized] = createSignal(
    props.group.api.isMaximized(),
  );

  const [isHovered, setIsHovered] = createSignal(false);

  onMount(() => {
    const groupElement = props.group.element;
    const handleMouseEnter = () => setIsHovered(true);
    const handleMouseLeave = () => setIsHovered(false);

    if (groupElement) {
      groupElement.addEventListener("mouseenter", handleMouseEnter);
      groupElement.addEventListener("mouseleave", handleMouseLeave);
    }

    setTimeout(() => {
      const dockview = props.getDockview();
      if (!dockview) return;

      const disposable = dockview.onDidMaximizedGroupChange(() => {
        setIsMaximized(props.group.api.isMaximized());
      });

      onCleanup(() => {
        disposable.dispose();
        if (groupElement) {
          groupElement.removeEventListener("mouseenter", handleMouseEnter);
          groupElement.removeEventListener("mouseleave", handleMouseLeave);
        }
      });
    }, 0);
  });

  const toggleMaximize = () => {
    if (props.group.api.isMaximized()) {
      props.group.api.exitMaximized();
    } else {
      props.group.api.maximize();
    }
  };

  const handleDetach = () => {
    const activePanel = props.group.activePanel;
    if (!activePanel) return;

    const params = activePanel.params as any;

    const id = activePanel.id;
    const viewType = params?.elementTag || "default";
    const title = params?.label || activePanel.title || "Detached view";

    if (params) {
      localStorage.setItem(`detached_payload_${id}`, JSON.stringify(params));
    }

    const targetRoute = buildPanelRoute({
      id,
      title,
      viewType,
      entryUrl: params?.entryUrl,
      isLocalFile: params?.isLocalFile,
      props: params,
      groupId: props.group.id,
    });

    const program = Effect.gen(function* () {
      const wm = yield* WindowBootstrapper;
      yield* wm.createChildFromCurrent(title, targetRoute);
    });

    getSystemRuntime()
      .runPromise(program)
      .then(() => {
        activePanel.api.close();
      })
      .catch(console.error);
  };

  return (
    <div
      class={`flex items-center h-full px-1 gap-1 transition-opacity duration-200 ${
        isHovered() ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
    >
      <button
        class="p-1.5 hover:bg-icon-btn-bg-hover rounded transition-all flex items-center justify-center text-sidebar-fg opacity-70 hover:opacity-100"
        onClick={toggleMaximize}
        title={isMaximized() ? "Restore" : "Maximize"}
      >
        {isMaximized() ? (
          <FiMinimize class="size-3.5" />
        ) : (
          <FiMaximize class="size-3.5" />
        )}
      </button>

      <button
        class="p-1.5 hover:bg-icon-btn-bg-hover rounded transition-all flex items-center justify-center text-sidebar-fg opacity-70 hover:opacity-100"
        onClick={handleDetach}
        title="Detach to new window"
      >
        <FiExternalLink class="size-3.5" />
      </button>
    </div>
  );
};
