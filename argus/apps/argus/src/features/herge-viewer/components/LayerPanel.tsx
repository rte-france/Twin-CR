/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component, For, Show } from "solid-js";
import { useHerge } from "../hooks/useHerge";

export const LayerPanel: Component = () => {
  const ctx = useHerge();

  return (
    <aside class="flex flex-col shrink-0 w-55 bg-sidebar-bg border-r border-border overflow-y-auto">
      <section class="p-3.5 border-b border-border">
        <h2 class="flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.13em] uppercase text-title-color mb-3 m-0">
          <span class="text-xs">🔍</span>
          Filtre Schéma
        </h2>
        <select
          class="w-full bg-bg border border-border rounded-md text-fg px-2 py-1.5 text-[11px] font-mono outline-none focus:border-links transition-colors cursor-pointer"
          value={ctx.selectedSchema() ?? ""}
          onChange={(e) => ctx.setSelectedSchema(e.currentTarget.value || null)}
        >
          <option value="">Tous les schémas (Vue globale)</option>
          <For each={ctx.schemasList()}>
            {(name) => <option value={name}>{name}</option>}
          </For>
        </select>
        <Show when={ctx.selectedSchema()}>
          <button
            onClick={() => ctx.setSelectedSchema(null)}
            class="mt-2 text-[9px] text-links hover:text-title-color underline cursor-pointer bg-transparent border-none p-0"
          >
            Réinitialiser la vue
          </button>
        </Show>
      </section>

      <section class="p-3.5 border-b border-border">
        <h2 class="flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.13em] uppercase text-title-color mb-3 m-0">
          <span class="text-xs">⊞</span>
          Couches
        </h2>
        <div class="flex flex-col gap-0.5">
          <For each={ctx.services}>
            {(svc) => {
              const isOn = () => ctx.visibility()[svc.id];
              return (
                <button
                  class="flex items-center gap-2 w-full p-1.5 rounded-md transition-colors text-left text-icons hover:bg-(--sidebar-active-bg) cursor-pointer bg-transparent border-none"
                  classList={{ "opacity-45": !isOn() }}
                  onClick={() => ctx.toggleService(svc.id)}
                  title={`${isOn() ? "Masquer" : "Afficher"} ${svc.label}`}
                >
                  <span
                    class="w-2 h-2 rounded-full shrink-0 transition-shadow duration-200"
                    style={{
                      background: svc.color,
                      "box-shadow": isOn() ? `0 0 7px ${svc.color}` : "none",
                    }}
                  />
                  <span class="text-[11px] flex-1 whitespace-nowrap overflow-hidden text-ellipsis">
                    {svc.label}
                  </span>
                  <span
                    class="relative w-7 h-4 rounded-full shrink-0 border border-white/10 transition-colors duration-250"
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

      <section class="p-3.5 border-b border-border">
        <h2 class="flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.13em] uppercase text-title-color mb-3 m-0">
          <span class="text-xs">◈</span>
          Légende active
        </h2>
        <select
          class="w-full bg-bg border border-border rounded-md text-fg px-2 py-1.5 text-[11px] font-mono outline-none focus:border-links transition-colors cursor-pointer"
          value={ctx.activeService()}
          onChange={(e) => ctx.setActiveService(e.currentTarget.value)}
        >
          <For each={ctx.services}>
            {(svc) => <option value={svc.id}>{svc.label}</option>}
          </For>
        </select>
      </section>

      <section class="p-3.5 flex-1">
        <h2 class="flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.13em] uppercase text-title-color mb-3 m-0">
          <span class="text-xs">ⓘ</span>
          Navigation
        </h2>
        <ul class="list-none p-0 m-0 text-[10px] text-icons leading-loose">
          <li>
            🖱 <b class="text-fg font-semibold">Molette</b> — zoom
          </li>
          <li>
            🖱 <b class="text-fg font-semibold">Glisser</b> — déplacer
          </li>
          <li>
            <b class="text-fg font-semibold">+ / −</b> — zoom boutons
          </li>
          <li>
            <b class="text-fg font-semibold">⌂</b> — étendue France
          </li>
        </ul>
      </section>
    </aside>
  );
};
