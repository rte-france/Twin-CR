/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { For, Show } from "solid-js";
import { useSubstationExplorerContext } from "../providers/SubstationExplorerProvider";
import { FiFile, FiMoreVertical } from "solid-icons/fi";
import { AiOutlineFolder, AiTwotoneFolder } from "solid-icons/ai";
import { getVoltageLevelColor } from "../utils";

export const SubstationList = () => {
  const { substations, toggleExpand, handleOpenSld, expanded } =
    useSubstationExplorerContext();

  return (
    <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
      <For each={substations()}>
        {(sub) => (
          <div class="flex flex-col">
            <div
              class="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-active-bg cursor-pointer transition-all border border-transparent hover:border-border-light"
              onClick={() => toggleExpand(sub.id)}
              onDblClick={() => handleOpenSld(sub.id, "sub")}
            >
              <div class="flex items-center gap-3 truncate">
                <Show
                  when={expanded().has(sub.id)}
                  fallback={<AiOutlineFolder class="size-5 text-icons" />}
                >
                  <div class="text-sidebar-active">
                    <AiTwotoneFolder class="size-5 opacity-80" />
                  </div>
                </Show>
                <span class="font-medium text-sm truncate">{sub.id}</span>
              </div>

              <div class="flex items-center gap-2">
                <Show when={sub.tso}>
                  <span class="px-1.5 py-0.5 rounded bg-sidebar-active-bg text-sidebar-active text-[10px] font-bold uppercase tracking-tight">
                    {sub.tso}
                  </span>
                </Show>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleOpenSld(sub.id, "sub");
                  }}
                  class="opacity-0 group-hover:opacity-100 p-1 hover:bg-icon-btn-bg-hover rounded text-icons transition-opacity"
                >
                  <FiMoreVertical class="size-4" />
                </button>
              </div>
            </div>

            <Show when={expanded().has(sub.id)}>
              <div class="ml-6 mt-1 border-l border-divider pl-2 space-y-0.5">
                <For each={sub.voltageLevels}>
                  {(vl) => (
                    <div
                      class="flex items-center justify-between p-2 text-xs hover:bg-sidebar-active-bg rounded group transition-colors cursor-pointer"
                      onDblClick={(e) => {
                        e.stopPropagation();
                        handleOpenSld(vl.id, "vl");
                      }}
                    >
                      <div class="flex items-center gap-2 group-hover:text-sidebar-non-existant text-fg">
                        <FiFile class="size-3" />
                        <span class="truncate">{vl.id}</span>
                      </div>
                      <div class="flex items-center gap-2">
                        <span class="font-mono tabular-nums">
                          {vl.nominal_v}kV
                        </span>
                        <div
                          class="w-1 h-3 rounded-full opacity-80"
                          classList={{
                            [getVoltageLevelColor(vl.nominal_v)]: true,
                            "bg-sidebar-active": !getVoltageLevelColor(
                              vl.nominal_v,
                            ),
                          }}
                        />
                      </div>
                    </div>
                  )}
                </For>
              </div>
            </Show>
          </div>
        )}
      </For>
    </div>
  );
};
