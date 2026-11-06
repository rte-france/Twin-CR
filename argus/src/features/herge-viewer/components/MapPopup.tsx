/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component, Show, For } from "solid-js";
import { Popover } from "@kobalte/core/popover";
import { openInCentral } from "@/utils/openInCentral";

interface MapPopupProps {
  data: any | null;
  pos: { x: number; y: number };
  onClose: () => void;
}

export const MapPopup: Component<MapPopupProps> = (props) => {
  const handleOpenSubstation = (value: string) => {
    const equipmentId = value.split("-")[0];
    openInCentral({
      id: `sub - ${equipmentId}`,
      title: `sub - ${equipmentId}`,
      elementTag: "sld-viewer",
      params: {
        equipmentId,
        type: "sub",
      },
    });
  };

  return (
    <Popover
      open={!!props.data}
      onOpenChange={(isOpen) => !isOpen && props.onClose()}
    >
      <Popover.Anchor
        style={{
          position: "absolute",
          left: `${props.pos.x}px`,
          top: `${props.pos.y}px`,
          width: "1px",
          height: "1px",
          "pointer-events": "none",
          "z-index": 400,
        }}
      />
      <Popover.Portal>
        <Popover.Content
          class="bg-popover-bg border border-popover-border rounded-lg shadow-(--popover-shadow) w-[320px] max-h-100 flex flex-col z-9999 animate-in fade-in zoom-in-95 duration-200"
          onInteractOutside={(e) => {
            if ((e.target as HTMLElement).closest(".map-canvas"))
              e.preventDefault();
          }}
        >
          <Popover.Arrow class="fill-popover-bg stroke-popover-border stroke-1" />

          <Show when={props.data}>
            {(feature) => (
              <>
                <div class="flex items-center justify-between p-3 border-b border-border bg-(--table-header-bg) rounded-t-lg">
                  <div class="flex items-center gap-2 overflow-hidden">
                    <span class="text-[9px] bg-media-bg px-1.5 py-0.5 rounded text-icons shrink-0 border border-border">
                      {feature()._serviceLabel}
                    </span>
                    <h3 class="text-[13px] font-bold text-title-color m-0 whitespace-nowrap overflow-hidden text-ellipsis truncate">
                      {feature().layerName}
                    </h3>
                  </div>
                  <Popover.CloseButton class="bg-transparent border-none text-icons text-sm cursor-pointer hover:text-red-500 transition-colors flex items-center ml-2">
                    ✕
                  </Popover.CloseButton>
                </div>

                <div class="p-3 overflow-y-auto flex flex-col gap-1.5">
                  <For
                    each={Object.entries(feature().attributes).filter(
                      ([k, v]) =>
                        v !== "Null" &&
                        v !== "" &&
                        k !== "Shape" &&
                        k !== "OBJECTID",
                    )}
                  >
                    {([key, value]) => (
                      <div class="flex justify-between items-start text-[11px] gap-3 border-b border-divider pb-1 last:border-none">
                        <span class="text-fg opacity-80 font-semibold shrink-0 max-w-[45%] uppercase">
                          {key}
                        </span>

                        <span class="text-fg text-right wrap-break-words">
                          <Show when={key === "IDR"} fallback={String(value)}>
                            <a
                              class="text-blue-500 hover:underline font-medium"
                              onClick={(_) => {
                                handleOpenSubstation(String(value));
                              }}
                            >
                              {String(value)}
                            </a>
                          </Show>
                        </span>
                      </div>
                    )}
                  </For>
                </div>
              </>
            )}
          </Show>
        </Popover.Content>
      </Popover.Portal>
    </Popover>
  );
};
