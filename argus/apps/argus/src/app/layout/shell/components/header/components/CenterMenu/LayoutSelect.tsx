/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Select } from "@kobalte/core/select";
import {
  usePlacement,
  type PlacementMode,
} from "@/app/layout/shell/providers/PlacementProvider";

const PLACEMENT_OPTIONS: { value: PlacementMode; label: string }[] = [
  { value: "within", label: "Tab" },
  { value: "right", label: "Right" },
  { value: "left", label: "Left" },
  { value: "above", label: "Up" },
  { value: "below", label: "Down" },
];

const getDirectionClass = (mode: PlacementMode) => {
  switch (mode) {
    case "within":
      return "inset-0.5 opacity-40";
    case "right":
      return "top-0 right-0 bottom-0 w-1/2";
    case "left":
      return "top-0 left-0 bottom-0 w-1/2";
    case "above":
      return "top-0 left-0 right-0 h-1/2";
    case "below":
      return "bottom-0 left-0 right-0 h-1/2";
    default:
      return "";
  }
};

export const LayoutSelect = () => {
  const { placement, setPlacement } = usePlacement();

  return (
    <Select
      options={PLACEMENT_OPTIONS}
      value={PLACEMENT_OPTIONS.find((o) => o.value === placement())}
      onChange={(option) => option && setPlacement(option.value)}
      optionValue="value"
      optionTextValue="label"
      itemComponent={(props) => (
        <Select.Item
          item={props.item}
          class="px-2 py-1.5 outline-none cursor-pointer flex items-center gap-2 hover:bg-fg/10 data-highlighted:bg-fg/10 data-selected:text-links transition-colors"
        >
          <div class="w-4 h-4 border border-fg/30 relative overflow-hidden shrink-0 bg-fg/5">
            <div
              class={`absolute bg-links/60 transition-all ${getDirectionClass(props.item.rawValue.value)}`}
            />
          </div>
          <Select.ItemLabel class="text-[11px] whitespace-nowrap">
            {props.item.textValue}
          </Select.ItemLabel>
        </Select.Item>
      )}
    >
      <Select.Trigger class="hover:bg-fg/10 px-1.5 h-full flex items-center gap-2 outline-none rounded-sm transition-colors group">
        <Select.Value<{ value: string; label: string }>>
          {(state) => (
            <div class="flex items-center gap-2">
              <div class="w-3.5 h-3.5 border border-fg/50 relative bg-fg/5 group-hover:border-fg">
                <div
                  class={`absolute bg-fg transition-all ${getDirectionClass(placement())}`}
                />
              </div>
              <span class="text-[10px] uppercase font-medium opacity-60 group-hover:opacity-100">
                {state.selectedOption()?.label}
              </span>
            </div>
          )}
        </Select.Value>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content class="bg-popover-bg border border-popover-border shadow-xl py-1 z-50 animate-in fade-in zoom-in-95 duration-100">
          <Select.Listbox class="outline-none min-w-37.5" />
        </Select.Content>
      </Select.Portal>
    </Select>
  );
};
