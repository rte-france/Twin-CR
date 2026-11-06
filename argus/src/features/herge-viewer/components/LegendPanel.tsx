/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component, For, Show, createSignal } from "solid-js";
import { Popover } from "@kobalte/core/popover";
import { FaSolidListUl } from "solid-icons/fa";
import { useHerge } from "../hooks/useHerge";

export const LegendPanel: Component = () => {
  const ctx = useHerge();
  const [collapsed, setCollapsed] = createSignal<Set<number>>(new Set());

  const toggle = (id: number) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <Popover placement="right-start">
      <Popover.Trigger
        class="w-6.5 h-6.5 bg-bg/85 backdrop-blur-md border border-border rounded-md text-icons flex items-center justify-center transition-colors hover:bg-(--theme-hover) hover:text-links hover:border-links shadow-sm cursor-pointer"
        title="Afficher la légende"
      >
        <FaSolidListUl size={12} />
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content class="bg-popover-bg border border-popover-border rounded-lg w-90 max-h-[65vh] flex flex-col shadow-(--popover-shadow) text-fg z-1050 animate-in slide-in-from-bottom-2 duration-200">
          <Popover.Arrow class="fill-popover-bg stroke-popover-border stroke-1" />

          <div class="px-4 pt-4 border-b border-border">
            <div class="flex justify-between items-center mb-3">
              <h3 class="m-0 text-[15px] font-semibold text-title-color">
                Symbologie
              </h3>
              <Popover.CloseButton class="bg-transparent border-none text-icons hover:text-icons-hover cursor-pointer text-base">
                ✕
              </Popover.CloseButton>
            </div>

            <div class="flex gap-4 overflow-x-auto pb-2 scrollbar-hide">
              <For each={ctx.services}>
                {(svc) => (
                  <button
                    class="bg-transparent border-none font-semibold text-[13px] cursor-pointer pb-1.5 whitespace-nowrap border-b-2 transition-colors"
                    classList={{
                      "text-links border-links": ctx.activeService() === svc.id,
                      "text-icons border-transparent hover:text-fg":
                        ctx.activeService() !== svc.id,
                    }}
                    onClick={() => ctx.setActiveService(svc.id)}
                  >
                    {svc.label}
                  </button>
                )}
              </For>
            </div>
          </div>

          <div class="p-4 overflow-y-auto flex-1">
            <Show when={ctx.legendLoading()}>
              <div class="flex items-center gap-2 text-[11px] text-icons py-2">
                <span class="w-3.5 h-3.5 border-2 border-border border-t-links rounded-full animate-spin shrink-0" />
                Chargement…
              </div>
            </Show>

            <Show when={!ctx.legendLoading() && ctx.legendError()}>
              <div class="flex gap-2.5 p-2.5 bg-warning-bg border border-warning-border rounded-md text-[11px] text-warning-icon">
                <span class="text-lg shrink-0">⚠</span>
                <div>
                  <p class="m-0 font-bold">Impossible de charger la légende.</p>
                  <p class="mt-1 text-[10px] opacity-80">
                    Vérifiez l'accès réseau
                  </p>
                </div>
              </div>
            </Show>

            <Show
              when={
                !ctx.legendLoading() &&
                !ctx.legendError() &&
                ctx.legendData().length === 0
              }
            >
              <p class="text-[11px] text-icons py-1.5 m-0">
                Aucune entrée de légende.
              </p>
            </Show>

            <Show
              when={
                !ctx.legendLoading() &&
                !ctx.legendError() &&
                ctx.legendData().length > 0
              }
            >
              <For each={ctx.legendData()}>
                {(layer) => {
                  const isOpen = () => !collapsed().has(layer.layerId);
                  return (
                    <div class="mb-2 bg-media-bg rounded-md border border-border overflow-hidden">
                      <button
                        class="flex items-center gap-1.5 w-full p-2 bg-bg border-b border-border text-left transition-colors text-fg hover:bg-(--theme-hover) cursor-pointer"
                        onClick={() => toggle(layer.layerId)}
                      >
                        <span
                          class="text-[10px] shrink-0 transition-colors"
                          style={{
                            color: isOpen() ? "var(--links)" : "var(--icons)",
                          }}
                        >
                          {isOpen() ? "●" : "○"}
                        </span>
                        <span class="text-[10px] font-semibold flex-1 tracking-wider">
                          {layer.layerName}
                        </span>
                        <span class="text-[9px] text-icons">
                          #{layer.layerId}
                        </span>
                        <span class="text-[9px] text-icons ml-1">
                          {isOpen() ? "▾" : "▸"}
                        </span>
                      </button>

                      <Show when={isOpen()}>
                        <ul class="list-none p-2 flex flex-col gap-1 m-0">
                          <For each={layer.legend}>
                            {(item) => (
                              <li class="flex items-center gap-2">
                                <span class="shrink-0 w-5 h-5 flex items-center justify-center">
                                  <Show
                                    when={item.imageData}
                                    fallback={
                                      <img
                                        class="block render-pixelated"
                                        width={item.width ?? 20}
                                        height={item.height ?? 20}
                                        alt={item.label}
                                        onError={(e) =>
                                          ((
                                            e.currentTarget as HTMLImageElement
                                          ).style.display = "none")
                                        }
                                      />
                                    }
                                  >
                                    <img
                                      class="block render-pixelated"
                                      width={item.width ?? 20}
                                      height={item.height ?? 20}
                                      alt={item.label}
                                      src={`data:${item.contentType ?? "image/png"};base64,${item.imageData}`}
                                    />
                                  </Show>
                                </span>
                                <span class="text-[10px] text-icons leading-snug">
                                  {item.label || "—"}
                                </span>
                              </li>
                            )}
                          </For>
                        </ul>
                      </Show>
                    </div>
                  );
                }}
              </For>
            </Show>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover>
  );
};
