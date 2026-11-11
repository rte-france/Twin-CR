/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import type { Component } from "solid-js";
import { ContextMenu } from "@kobalte/core/context-menu";
import type { DockviewPanelApi } from "dockview-core";
import { FiLayout, FiSidebar, FiArrowDown, FiX } from "solid-icons/fi";
import { Effect } from "effect";
import { WindowBootstrapper } from "@/services/window-bootstrap";
import { getSystemRuntime } from "@/utils/getSystemRuntime";

interface CustomTabProps {
  api: DockviewPanelApi;
  title: string;
  params: any;
}

export const DockviewTab: Component<CustomTabProps> = (props) => {
  const urlParams = new URLSearchParams(window.location.search);
  const parentLabel = urlParams.get("parent");
  const isDetached = !!parentLabel;

  const handleClose = () => props.api.close();

  const handleCloseOthers = () => {
    const group = props.api.group;
    if (!group) return;
    const panelsToClose = group.panels.filter((p) => p.id !== props.api.id);
    panelsToClose.forEach((p) => p.api.close());
  };

  const handleCloseAll = () => {
    props.api.group?.model.closeAllPanels();
  };

  const othersDisabled = () => (props.api.group?.panels.length ?? 0) <= 1;

  const moveTo = (target: "left" | "right" | "central" | "bottom") => {
    window.dispatchEvent(
      new CustomEvent("argus:move-panel", {
        detail: {
          id: props.api.id,
          target,
          manifest: props.params,
        },
      }),
    );
  };

  const handleDetach = () => {
    const id = props.api.id;
    const title = props.params?.label || props.title || "Detached Panel";

    if (props.params) {
      localStorage.setItem(
        `detached_payload_${id}`,
        JSON.stringify(props.params),
      );
    }

    const targetRoute = encodeURIComponent(
      `/floating/${props.params?.elementTag || "default"}/${id}`,
    );

    const program = Effect.gen(function* () {
      const wm = yield* WindowBootstrapper;
      yield* wm.createChildFromCurrent(title, targetRoute);
    });

    getSystemRuntime()
      .runPromise(program)
      .then(() => {
        props.api.close();
      })
      .catch(console.error);
  };

  const itemClass =
    "relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-icon-btn-bg-hover focus:bg-icon-btn-bg-hover data-[disabled]:pointer-events-none data-[disabled]:opacity-50";

  return (
    <ContextMenu>
      <ContextMenu.Trigger
        class="group flex h-full w-full items-center justify-between px-2 cursor-pointer relative"
        onContextMenu={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
        onPointerUp={(e) => {
          if (e.button === 1) {
            e.stopPropagation();
            handleClose();
          }
        }}
      >
        <span class="truncate pr-6">
          {props.params?.file?.filename || props.title}
        </span>
        <button
          class="absolute right-1 p-1 opacity-0 group-hover:opacity-100 hover:bg-icon-btn-bg-hover rounded transition-all flex items-center justify-center text-sidebar-fg"
          onClick={(e) => {
            e.stopPropagation();
            handleClose();
          }}
          title="Close"
        >
          <FiX class="size-3.5" />
        </button>
      </ContextMenu.Trigger>

      {/* Dropdown Menu */}
      <ContextMenu.Portal>
        <ContextMenu.Content class="z-99999 min-w-48 overflow-hidden rounded-md border border-border bg-sidebar-bg p-1.5 text-sidebar-fg shadow-2xl outline-none">
          <ContextMenu.Item onSelect={handleClose} class={itemClass}>
            Close
          </ContextMenu.Item>

          <ContextMenu.Item
            onSelect={handleCloseOthers}
            disabled={othersDisabled()}
            class={itemClass}
          >
            Close Others
          </ContextMenu.Item>

          <ContextMenu.Item onSelect={handleCloseAll} class={itemClass}>
            Close All
          </ContextMenu.Item>

          <ContextMenu.Separator class="-mx-1 my-1.5 h-px bg-border" />

          {!isDetached && (
            <ContextMenu.Sub>
              <ContextMenu.SubTrigger
                class={`${itemClass} justify-between data-expanded:bg-icon-btn-bg-hover`}
              >
                Move To...
              </ContextMenu.SubTrigger>
              <ContextMenu.Portal>
                <ContextMenu.SubContent class="z-99999 min-w-40 overflow-hidden rounded-md border border-border bg-sidebar-bg p-1.5 text-sidebar-fg shadow-2xl outline-none">
                  <ContextMenu.Item
                    onSelect={() => moveTo("central")}
                    class={`gap-2 ${itemClass}`}
                  >
                    <FiLayout class="opacity-70" /> Center
                  </ContextMenu.Item>
                  <ContextMenu.Item
                    onSelect={() => moveTo("bottom")}
                    class={`gap-2 ${itemClass}`}
                  >
                    <FiArrowDown class="opacity-70" /> Bottom Panel
                  </ContextMenu.Item>
                  <ContextMenu.Item
                    onSelect={() => moveTo("left")}
                    class={`gap-2 ${itemClass}`}
                  >
                    <FiSidebar class="opacity-70 rotate-180" /> Left Sidebar
                  </ContextMenu.Item>
                  <ContextMenu.Item
                    onSelect={() => moveTo("right")}
                    class={`gap-2 ${itemClass}`}
                  >
                    <FiSidebar class="opacity-70" /> Right Sidebar
                  </ContextMenu.Item>
                </ContextMenu.SubContent>
              </ContextMenu.Portal>
            </ContextMenu.Sub>
          )}

          {!isDetached && (
            <ContextMenu.Separator class="-mx-1 my-1.5 h-px bg-border" />
          )}

          <ContextMenu.Item class={itemClass}>
            Add to Favorites
          </ContextMenu.Item>

          <ContextMenu.Separator class="-mx-1 my-1.5 h-px bg-border" />

          <ContextMenu.Item
            class={`gap-2 ${itemClass}`}
            onSelect={handleDetach}
          >
            Detach Panel
          </ContextMenu.Item>
        </ContextMenu.Content>
      </ContextMenu.Portal>
    </ContextMenu>
  );
};
