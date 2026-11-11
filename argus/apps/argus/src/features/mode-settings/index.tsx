/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show } from "solid-js";
import { Select } from "@kobalte/core/select";
import { TbDeviceGamepad2, TbChartDots } from "solid-icons/tb";

import { useAppMode } from "@/hooks/useAppMode";
import { Mode } from "@/services/app-mode";

const MODE_OPTIONS = [
  { value: Mode.GameMaster, label: Mode.GameMaster },
  { value: Mode.Scada, label: Mode.Scada },
];

export const ModeStatus = () => {
  const [mode, setMode] = useAppMode();

  return (
    <Select
      options={MODE_OPTIONS}
      value={MODE_OPTIONS.find((o) => o.value === mode())}
      onChange={(option) => {
        if (option) setMode(option.value as Mode);
      }}
      optionValue="value"
      optionTextValue="label"
      itemComponent={(props) => (
        <Select.Item
          item={props.item}
          class="flex items-center gap-2 px-2 py-1 outline-none cursor-pointer hover:bg-theme-hover data-highlighted:bg-theme-hover data-selected:text-links transition-colors"
        >
          <Show
            when={props.item.rawValue.value === Mode.GameMaster}
            fallback={<TbChartDots class="size-3" />}
          >
            <TbDeviceGamepad2 class="size-3" />
          </Show>
          <Select.ItemLabel>{props.item.textValue}</Select.ItemLabel>
        </Select.Item>
      )}
    >
      <Select.Trigger class="text-xs px-2 h-full flex items-center gap-1 transition-colors outline-none cursor-pointer">
        <Show
          when={mode() === Mode.GameMaster}
          fallback={<TbChartDots class="size-4" />}
        >
          <TbDeviceGamepad2 class="size-4" />
        </Show>
        <Select.Value<(typeof MODE_OPTIONS)[0]>>
          {(state) => state.selectedOption()?.label}
        </Select.Value>
      </Select.Trigger>

      <Select.Portal>
        <Select.Content class="bg-popover-bg border border-popover-border shadow-md rounded text-fg text-[11px] py-1 z-50 origin-(--kb-select-content-transform-origin) animate-in fade-in zoom-in-95">
          <Select.Listbox class="outline-none" />
        </Select.Content>
      </Select.Portal>
    </Select>
  );
};
