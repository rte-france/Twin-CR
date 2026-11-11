/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, For, Show } from "solid-js";
import { DropdownMenu } from "@kobalte/core/dropdown-menu";
import { FiMenu, FiChevronRight } from "solid-icons/fi";
import { useNadContext } from "../hooks/useNadContext";
import { useEditorContext } from "../hooks/useEditorContext";
import { VL_COLORS } from "../types";

const triggerClass =
  "hover:bg-[var(--sidebar-active-bg)] rounded transition-colors text-[var(--fg)] opacity-80 hover:opacity-100 outline-none data-[expanded]:bg-[var(--sidebar-active-bg)] data-[expanded]:text-[var(--links)]";
const contentClass =
  "min-w-[200px] bg-[var(--popover-bg)] border border-[var(--popover-border)] rounded-md shadow-[var(--popover-shadow)] p-1 z-50 outline-none animate-in fade-in zoom-in-95 duration-100";
const itemClass =
  "relative flex items-center justify-between px-2 py-2 text-[11px] text-[var(--fg)] outline-none cursor-pointer rounded hover:bg-[var(--sidebar-active-bg)] hover:text-[var(--links)] data-[highlighted]:bg-[var(--sidebar-active-bg)] data-[highlighted]:text-[var(--links)] transition-colors data-[disabled]:opacity-40 data-[disabled]:pointer-events-none";
const subTriggerClass =
  "flex items-center justify-between w-full px-2 py-2 text-[11px] text-[var(--fg)] outline-none cursor-pointer rounded data-[highlighted]:bg-[var(--sidebar-active-bg)] data-[highlighted]:text-[var(--links)] transition-colors";
const separatorClass = "h-px bg-[var(--border)] my-1 -mx-1 opacity-50";

export const NadMenuEditor: Component = () => {
  const ctx = useNadContext();
  const editor = useEditorContext();

  return (
    <DropdownMenu>
      <DropdownMenu.Trigger class={triggerClass}>
        <FiMenu size={16} />
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content class={contentClass}>
          <DropdownMenu.Sub>
            <DropdownMenu.SubTrigger class={subTriggerClass}>
              Edit Mode
              <Show when={editor.editorState.isEditing}>
                <span class="ml-auto mr-2 w-1.5 h-1.5 rounded-full bg-[var(--links)] animate-pulse shadow-[0_0_5px_var(--links)]" />
              </Show>
              <FiChevronRight size={12} class="opacity-50" />
            </DropdownMenu.SubTrigger>
            <DropdownMenu.Portal>
              <DropdownMenu.SubContent class={contentClass}>
                <DropdownMenu.Item
                  class={`${itemClass} ${editor.editorState.isEditing ? "text-[var(--links)] font-bold" : ""}`}
                  onClick={() => editor.toggleEditing()}
                >
                  {editor.editorState.isEditing
                    ? "Exit Edit Mode"
                    : "Enter Edit Mode"}
                </DropdownMenu.Item>
                <DropdownMenu.Separator class={separatorClass} />
                <DropdownMenu.Item
                  class={itemClass}
                  disabled={!editor.editorState.isEditing}
                  onClick={() => editor.setTool("select")}
                >
                  Select (S)
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  class={itemClass}
                  disabled={!editor.editorState.isEditing}
                  onClick={() => editor.setTool("move")}
                >
                  Move Node (G)
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  class={itemClass}
                  disabled={!editor.editorState.isEditing}
                  onClick={() => editor.setTool("pan")}
                >
                  Pan (P)
                </DropdownMenu.Item>
                <DropdownMenu.Separator class={separatorClass} />
                <DropdownMenu.Item
                  class={itemClass}
                  disabled={!editor.editorState.isEditing}
                  onClick={() => editor.undo()}
                >
                  Undo
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  class={itemClass}
                  disabled={!editor.editorState.isEditing}
                  onClick={() => editor.redo()}
                >
                  Redo
                </DropdownMenu.Item>
              </DropdownMenu.SubContent>
            </DropdownMenu.Portal>
          </DropdownMenu.Sub>

          <DropdownMenu.Sub>
            <DropdownMenu.SubTrigger class={subTriggerClass}>
              View & Layout <FiChevronRight size={12} class="opacity-50" />
            </DropdownMenu.SubTrigger>
            <DropdownMenu.Portal>
              <DropdownMenu.SubContent class={contentClass}>
                <DropdownMenu.RadioGroup
                  value={ctx.layoutMode()}
                  onChange={(v) => ctx.setLayoutMode(v as any)}
                >
                  <DropdownMenu.RadioItem value="default" class={itemClass}>
                    Default{" "}
                    <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                  </DropdownMenu.RadioItem>
                  <DropdownMenu.RadioItem value="manhattan" class={itemClass}>
                    Manhattan{" "}
                    <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                  </DropdownMenu.RadioItem>
                  <DropdownMenu.RadioItem value="octolinear" class={itemClass}>
                    Octolinear{" "}
                    <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                  </DropdownMenu.RadioItem>
                </DropdownMenu.RadioGroup>
                <DropdownMenu.Separator class={separatorClass} />
                <DropdownMenu.RadioGroup
                  value={ctx.flowType()}
                  onChange={(v) => ctx.setFlowType(v as any)}
                >
                  <DropdownMenu.RadioItem value="active" class={itemClass}>
                    Active (P){" "}
                    <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                  </DropdownMenu.RadioItem>
                  <DropdownMenu.RadioItem value="reactive" class={itemClass}>
                    Reactive (Q){" "}
                    <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                  </DropdownMenu.RadioItem>
                  <DropdownMenu.RadioItem value="current" class={itemClass}>
                    Current (I){" "}
                    <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                  </DropdownMenu.RadioItem>
                </DropdownMenu.RadioGroup>
                <DropdownMenu.Separator class={separatorClass} />
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.hideDisconnected()}
                  onChange={ctx.setHideDisconnected}
                >
                  Hide Disconnected{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
              </DropdownMenu.SubContent>
            </DropdownMenu.Portal>
          </DropdownMenu.Sub>

          <DropdownMenu.Sub>
            <DropdownMenu.SubTrigger class={subTriggerClass}>
              Layers <FiChevronRight size={12} class="opacity-50" />
            </DropdownMenu.SubTrigger>
            <DropdownMenu.Portal>
              <DropdownMenu.SubContent class={contentClass}>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.layers.labels}
                  onChange={(c) => ctx.setLayers("labels", c)}
                >
                  Labels{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.layers.edgeInfos}
                  onChange={(c) => ctx.setLayers("edgeInfos", c)}
                >
                  Edge Infos{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.layers.injections}
                  onChange={(c) => ctx.setLayers("injections", c)}
                >
                  Injections{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
              </DropdownMenu.SubContent>
            </DropdownMenu.Portal>
          </DropdownMenu.Sub>

          <DropdownMenu.Sub>
            <DropdownMenu.SubTrigger class={subTriggerClass}>
              Equipment <FiChevronRight size={12} class="opacity-50" />
            </DropdownMenu.SubTrigger>
            <DropdownMenu.Portal>
              <DropdownMenu.SubContent class={contentClass}>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.equipmentLayers.generator}
                  onChange={(c) => ctx.setEquipmentLayers("generator", c)}
                >
                  Generators{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.equipmentLayers.load}
                  onChange={(c) => ctx.setEquipmentLayers("load", c)}
                >
                  Loads{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.equipmentLayers.battery}
                  onChange={(c) => ctx.setEquipmentLayers("battery", c)}
                >
                  Batteries{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
                <DropdownMenu.CheckboxItem
                  class={itemClass}
                  checked={ctx.equipmentLayers.capacitor}
                  onChange={(c) => ctx.setEquipmentLayers("capacitor", c)}
                >
                  Capacitors{" "}
                  <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                </DropdownMenu.CheckboxItem>
              </DropdownMenu.SubContent>
            </DropdownMenu.Portal>
          </DropdownMenu.Sub>

          <DropdownMenu.Sub>
            <DropdownMenu.SubTrigger class={subTriggerClass}>
              Voltages <FiChevronRight size={12} class="opacity-50" />
            </DropdownMenu.SubTrigger>
            <DropdownMenu.Portal>
              <DropdownMenu.SubContent class={contentClass}>
                <For each={Object.entries(VL_COLORS)}>
                  {([key, info]) => (
                    <DropdownMenu.CheckboxItem
                      class={itemClass}
                      checked={ctx.vlLayers[key]}
                      onChange={(c) => ctx.setVlLayers(key, c)}
                    >
                      <div class="flex items-center gap-2">
                        <span
                          class="w-2 h-2 rounded-full"
                          style={`background-color: ${info.color}`}
                        />
                        {info.label}
                      </div>
                      <DropdownMenu.ItemIndicator>✓</DropdownMenu.ItemIndicator>
                    </DropdownMenu.CheckboxItem>
                  )}
                </For>
              </DropdownMenu.SubContent>
            </DropdownMenu.Portal>
          </DropdownMenu.Sub>

          <DropdownMenu.Separator class={separatorClass} />

          <DropdownMenu.Item class={itemClass} onClick={() => ctx.resetView()}>
            Reset View
          </DropdownMenu.Item>
          <DropdownMenu.Item
            class={itemClass}
            onClick={() => ctx.fitCanvas()()}
          >
            Fit Canvas
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu>
  );
};
