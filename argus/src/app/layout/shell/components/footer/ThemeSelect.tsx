/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Select } from "@kobalte/core/select";
import { useTheme } from "../../providers/ThemeProvider";

const THEME_OPTIONS = [
  { value: "light", label: "Clair" },
  { value: "dark", label: "Sombre" },
  { value: "system", label: "Système" },
];

export const ThemeSelect = () => {
  const { theme, setTheme } = useTheme();

  return (
    <Select
      options={THEME_OPTIONS}
      value={THEME_OPTIONS.find((o) => o.value === theme())}
      onChange={(option) => {
        if (option) setTheme(option.value as "light" | "dark" | "system");
      }}
      optionValue="value"
      optionTextValue="label"
      itemComponent={(props) => (
        <Select.Item
          item={props.item}
          class="px-2 py-1 outline-none cursor-pointer hover:bg-theme-hover data-highlighted:bg-theme-hover data-selected:text-links transition-colors"
        >
          <Select.ItemLabel>{props.item.textValue}</Select.ItemLabel>
        </Select.Item>
      )}
    >
      <Select.Trigger class="uppercase font-bold hover:bg-white/20 px-2 h-full flex items-center gap-1 transition-colors outline-none cursor-pointer">
        <Select.Value<(typeof THEME_OPTIONS)[0]>>
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
