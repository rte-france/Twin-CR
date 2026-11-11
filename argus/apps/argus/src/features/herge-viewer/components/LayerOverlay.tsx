/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component, For } from "solid-js";
import { Popover } from "@kobalte/core/popover";
import { FaSolidLayerGroup } from "solid-icons/fa";
import { useHerge } from "../hooks/useHerge";

export const LayerOverlay: Component = () => {
  const ctx = useHerge();

  return (
    <Popover placement="right-start">
      <Popover.Trigger
        class="w-6.5 h-6.5 bg-bg/85 backdrop-blur-md border border-border rounded-md text-icons flex items-center justify-center transition-colors hover:bg-(--theme-hover) hover:text-links hover:border-links shadow-sm cursor-pointer"
        title="Gérer les couches"
      >
        <FaSolidLayerGroup size={12} />
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content class="bg-popover-bg border border-popover-border text-fg shadow-(--popover-shadow) rounded-lg p-4 w-80 z-1050 animate-in fade-in zoom-in-95 duration-200">
          <Popover.Arrow class="fill-popover-bg stroke-popover-border stroke-1" />

          <div class="flex justify-between items-center mb-4">
            <h3 class="m-0 text-[15px] font-semibold text-title-color">
              Paramètres de la carte
            </h3>
            <Popover.CloseButton class="bg-transparent border-none text-icons hover:text-icons-hover cursor-pointer text-base">
              ✕
            </Popover.CloseButton>
          </div>

          <div class="flex flex-col gap-4">
            <section>
              <label class="block text-[11px] uppercase tracking-wide text-fg opacity-70 mb-2">
                Couches affichées
              </label>
              <div class="flex flex-col gap-1">
                <For each={ctx.services}>
                  {(svc) => {
                    const isOn = () => ctx.visibility()[svc.id];
                    return (
                      <button
                        class="flex items-center gap-2 w-full p-2 rounded-md transition-colors text-left text-fg hover:bg-(--theme-hover) cursor-pointer"
                        classList={{ "opacity-45": !isOn() }}
                        onClick={() => ctx.toggleService(svc.id)}
                        title={`${isOn() ? "Masquer" : "Afficher"} ${svc.label}`}
                      >
                        <span
                          class="w-2 h-2 rounded-full shrink-0 transition-shadow duration-200"
                          style={{
                            background: svc.color,
                            "box-shadow": isOn()
                              ? `0 0 7px ${svc.color}`
                              : "none",
                          }}
                        />
                        <span class="text-[11px] flex-1 whitespace-nowrap overflow-hidden text-ellipsis">
                          {svc.label}
                        </span>
                        <span
                          class="relative w-7 h-4 rounded-full shrink-0 border border-border transition-colors duration-250"
                          style={{
                            background: isOn() ? svc.color : "var(--media-bg)",
                          }}
                        >
                          <span
                            class="absolute top-px left-px w-3 h-3 rounded-full bg-bg transition-transform duration-200 shadow-sm"
                            style={{
                              transform: isOn()
                                ? "translateX(12px)"
                                : "translateX(0px)",
                            }}
                          />
                        </span>
                      </button>
                    );
                  }}
                </For>
              </div>
            </section>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover>
  );
};
