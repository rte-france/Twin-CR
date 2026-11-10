/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { type Component, For, Show, createResource, createSignal } from "solid-js";
import { useSearchParams, A } from "@solidjs/router";
import { FiRadio, FiKey, FiLogIn, FiLayers, FiActivity, FiLock, FiUnlock } from "solid-icons/fi";
import { SessionAPI } from "@/features/session";

export const JoinSession: Component = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [accessKey, setAccessKey] = createSignal("");

  const [stations] = createResource(SessionAPI.fetchStations);
  const selectedId = () => searchParams.station || stations()?.[0]?.id;

  const handleSelect = (id: string) => {
    setAccessKey("");
    setSearchParams({ station: id }, { replace: true });
  };

  const selectedStation = () => stations()?.find(s => s.id === selectedId());

  return (
    <div class="flex h-full gap-4">
      <aside class="w-1/4 min-w-70 flex flex-col">
        <div class="flex-1 min-h-0 flex flex-col h-full bg-white text-slate-800 font-sans select-none border border-slate-200 rounded-md overflow-hidden shadow-sm">
          <div class="p-4 space-y-4 border-b border-slate-200 bg-slate-50">
            <div class="flex items-center justify-between text-xs text-slate-500">
              <span class="font-medium uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <FiLayers class="size-3.5" /> Group x Station
              </span>
              <span class="font-medium">
                {stations()?.length || 0} station{(stations()?.length || 0) > 1 ? "s" : ""}
              </span>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-white">
            <Show when={!stations.loading}>
              <For each={stations()}>
                {(item) => {
                  const isSelected = () => selectedId() === item.id;
                  return (
                    <div
                      onClick={() => handleSelect(item.id)}
                      class="group flex flex-col p-2 rounded-md cursor-pointer transition-all border"
                      classList={{
                        "bg-slate-100 border-slate-300 shadow-sm": isSelected(),
                        "border-transparent hover:bg-slate-50 hover:border-slate-200": !isSelected()
                      }}
                    >
                      <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center gap-2 truncate">
                          <Show when={item.requiresKey} fallback={<FiUnlock class="size-3 text-slate-400 shrink-0" />}>
                            <FiLock class="size-3 text-amber-500 shrink-0" />
                          </Show>
                          <span class="font-medium text-sm truncate">{item.name}</span>
                        </div>
                        <div
                          class="size-2 rounded-full shrink-0"
                          classList={{
                            "bg-green-500": item.status === "waiting",
                            "bg-blue-500": item.status === "in-progress"
                          }}
                        />
                      </div>
                      <span class="text-[10px] font-medium text-slate-400 uppercase tracking-widest mt-1 truncate pl-5">
                        {item.group}
                      </span>
                    </div>
                  );
                }}
              </For>
            </Show>
          </div>
        </div>
      </aside>

      <section class="flex-1 flex flex-col min-h-0">
        <div class="flex-1 min-h-0 flex flex-col h-full bg-white text-slate-800 font-sans select-none border border-slate-200 rounded-md overflow-hidden shadow-sm">
          <div class="p-4 space-y-4 border-b border-slate-200 bg-slate-50 shrink-0">
            <div class="flex items-center justify-between text-xs text-slate-500 h-7">
              <span class="font-medium uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                 <FiActivity class="size-3.5" /> Connection
              </span>
              <button class="text-[10px] uppercase font-medium px-2 py-1 rounded bg-white border border-slate-300 hover:bg-slate-100 text-slate-600 transition-colors shadow-sm flex items-center gap-1">
                <FiKey class="size-3" /> Station Key
              </button>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-6 custom-scrollbar bg-white flex flex-col">
            <Show when={selectedStation()}>
              {(station) => (
                <>
                  <div class="flex items-center gap-4 mb-8">
                    <div class="p-3 bg-blue-50 text-blue-600 rounded-md border border-blue-100">
                      <FiRadio class="size-6" />
                    </div>
                    <div class="flex flex-col min-w-0">
                      <h3 class="font-medium text-xl text-slate-800 truncate">
                        {station().name}
                      </h3>
                      <span class="text-xs font-medium text-slate-500 uppercase tracking-widest mt-1">
                        Group: {station().group}
                      </span>
                    </div>
                  </div>

                  <div class="flex flex-col gap-6 max-w-md">
                    <div class="flex flex-col gap-1.5">
                      <span class="text-[10px] font-medium text-slate-500 uppercase tracking-widest pl-1">
                        Current Status
                      </span>
                      <div class="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-2 rounded">
                         <div
                            class="size-2.5 rounded-full shrink-0"
                            classList={{
                              "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]": station().status === "waiting",
                              "bg-blue-500": station().status === "in-progress"
                            }}
                          />
                          <span class="text-sm font-medium" classList={{
                            "text-green-700": station().status === "waiting",
                            "text-blue-700": station().status === "in-progress"
                          }}>
                            {station().status === "waiting" ? "Waiting for players" : "Session in progress"}
                          </span>
                      </div>
                    </div>

                    <div class="flex flex-col gap-1.5">
                      <label class="text-[10px] font-medium text-slate-500 uppercase tracking-widest pl-1 flex items-center gap-1">
                         Access Key <Show when={station().requiresKey}><span class="text-amber-500">(Required)</span></Show>
                      </label>
                      <input
                        type="text"
                        value={accessKey()}
                        onInput={(e) => setAccessKey(e.currentTarget.value)}
                        placeholder="XXXX-XXXX"
                        class="bg-white border border-slate-300 rounded px-3 py-2 text-sm outline-none focus:border-blue-500 text-slate-800 placeholder-slate-400 transition-colors shadow-sm font-mono uppercase"
                      />
                    </div>
                  </div>

                  <div class="mt-auto pt-6 flex justify-between items-center border-t border-slate-100">
                     <span class="text-xs font-medium text-slate-400">
                       Ready to connect to session...
                     </span>
                     {/* URL STATE NAVIGATION */}
                     <A
                       href={`/waiting-room/${station().id}`}
                       class="px-6 py-2 rounded border border-blue-600 bg-blue-600 hover:bg-blue-700 text-white transition-colors shadow-sm text-sm font-medium flex items-center gap-2"
                     >
                       <FiLogIn class="size-4" /> Join Session
                     </A>
                  </div>
                </>
              )}
            </Show>
          </div>
        </div>
      </section>
    </div>
  );
};

export default JoinSession;
