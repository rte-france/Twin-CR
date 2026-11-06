/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Select } from "@kobalte/core/select";
import { type Component, For } from "solid-js";
import { useLayout } from "../../providers/LayoutProvider";

type LayoutType =
  | "sidebar-left"
  | "split-view"
  | "bottom-panel"
  | "sidebar-right";

const LAYOUT_OPTIONS: { value: LayoutType; label: string } = [
  { value: "sidebar-left", label: "Barre latérale gauche" },
  { value: "split-view", label: "Vue scindée" },
  { value: "bottom-panel", label: "Panneau inférieur" },
  { value: "sidebar-right", label: "Barre latérale droite" },
];

const LayoutIcon: Component<{ type: LayoutType; active?: boolean }> = (
  props,
) => {
  return (
    <div
      class={`w-4 h-4 border border-fg/50 relative flex overflow-hidden rounded-[1px] ${props.active ? "border-links" : "opacity-70"}`}
    >
      <div
        class={`bg-fg/20 border-r border-fg/30 ${props.type === "sidebar-left" ? "w-1/3 bg-links/40" : "w-0"}`}
      />

      <div class="flex-1 flex flex-col">
        <div class="flex-1 flex">
          {/* Split View */}
          <div
            class={`border-r border-fg/20 ${props.type === "split-view" ? "w-1/2 bg-links/40" : "w-0"}`}
          />
          <div class="flex-1" />
        </div>
        {/* Bottom Panel */}
        <div
          class={`border-t border-fg/30 ${props.type === "bottom-panel" ? "h-1/3 bg-links/40" : "h-0"}`}
        />
      </div>

      {/* Sidebar Right */}
      <div
        class={`bg-fg/20 border-l border-fg/30 ${props.type === "sidebar-right" ? "w-1/3 bg-links/40" : "w-0"}`}
      />
    </div>
  );
};

export const LayoutSelect = () => {
  const { layout, setLayout } = useLayout();

  return (
    <Select
      options={LAYOUT_OPTIONS}
      value={LAYOUT_OPTIONS.find((o) => o.value === layout())}
      onChange={(option) => {
        if (option) setLayout(option.value as LayoutType);
      }}
      optionValue="value"
      optionTextValue="label"
      itemComponent={(props) => (
        <Select.Item
          item={props.item}
          class="px-2 py-1.5 outline-none cursor-pointer flex items-center gap-2 hover:bg-fg/10 data-highlighted:bg-fg/10 data-selected:text-links transition-colors"
        >
          <LayoutIcon type={props.item.rawValue.value} />
          <Select.ItemLabel class="text-[11px]">
            {props.item.textValue}
          </Select.ItemLabel>
        </Select.Item>
      )}
    >
      <Select.Trigger class="hover:bg-fg/10 px-2 h-full flex items-center gap-1 transition-colors outline-none cursor-pointer">
        <Select.Value<(typeof LAYOUT_OPTIONS)[0]>>
          {(state) => (
            <div class="flex items-center">
              <LayoutIcon
                type={state.selectedOption()?.value || "sidebar-left"}
              />
            </div>
          )}
        </Select.Value>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content class="bg-popover-bg border border-popover-border shadow-md rounded text-fg py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
          <Select.Listbox class="outline-none min-w-[180px]" />
        </Select.Content>
      </Select.Portal>
    </Select>
  );
};
