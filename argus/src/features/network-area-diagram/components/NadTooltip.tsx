/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, Show, createSignal } from "solid-js";
import { useNadContext } from "../hooks/useNadContext";
import { typeOf } from "@/services/network-properties";
import { SingleElementPopup } from "@/features/network-properties-viewer/components/SingleElementPopup";

export const NadTooltip: Component = () => {
  const ctx = useNadContext();
  const [popupOpen, setPopupOpen] = createSignal(false);
  const [componentType, setComponentType] = createSignal<string | null>(null);

  const handleOpenPopup = async (equipmentId: string) => {
    const type = await typeOf(equipmentId);
    if (!type) {
      console.error("Failed to fetch component type of", equipmentId);
      return;
    }
    setComponentType(type);
    setPopupOpen(true);
  };

  return (
    <>
      <Show when={ctx.selected()}>
        {(item) => (
          <div class="absolute bottom-6 right-6 w-72 bg-surface/95 backdrop-blur-md border border-border text-text p-4 z-40 rounded-lg shadow-popout animate-in slide-in-from-bottom-5">
            <div class="flex justify-between items-start mb-2">
              <span
                class={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded ${
                  item().elementType === "node"
                    ? "bg-status-success-weak text-text-success"
                    : "bg-status-info-weak text-text-info"
                }`}
              >
                {item().elementType}
              </span>
              <button
                onClick={() => ctx.setSelected(null)}
                class="text-icon hover:text-icon-hover transition-colors"
              >
                ✕
              </button>
            </div>
            <h3 class="text-sm font-semibold mb-1 break-all leading-tight">
              {item().label}
            </h3>
            <div class="mt-3 pt-3 border-t border-border">
              <button
                onClick={() => handleOpenPopup(item().equipmentId)}
                class="w-full px-3 py-1.5 text-xs rounded bg-[var(--links)] text-white hover:opacity-90 transition-all"
              >
                Properties
              </button>
            </div>
          </div>
        )}
      </Show>

      <Show when={popupOpen() && componentType() && ctx.selected()}>
        <SingleElementPopup
          open={popupOpen()}
          onClose={() => setPopupOpen(false)}
          elementId={ctx.selected()!.equipmentId}
          componentType={componentType()!}
        />
      </Show>
    </>
  );
};
