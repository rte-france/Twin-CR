/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { type Component, For, Show, createSignal, createResource } from "solid-js";
import { useParams } from "@solidjs/router";
import { FiUsers, FiMessageSquare, FiCheck, FiShield, FiTarget, FiCpu, FiClock } from "solid-icons/fi";
import { SessionAPI } from "@/features/session";

type Player = { id: string; name: string; isReady: boolean; };

const getInitials = (name: string) => name.substring(0, 2).toUpperCase();

const PlayerSlot: Component<{ player: Player | null; roleColor: string }> = (props) => {
  return (
    <Show
      when={props.player}
      fallback={
        <div class="h-14 border-2 border-dashed border-slate-300 rounded-lg flex items-center justify-center bg-slate-50/50 transition-colors hover:bg-slate-100 cursor-pointer">
          <span class="text-xs font-medium text-slate-400 uppercase tracking-widest">
            Empty Slot
          </span>
        </div>
      }
    >
      <div class="h-14 border border-slate-200 rounded-lg flex items-center justify-between p-3 bg-white shadow-sm transition-all hover:border-slate-300 group cursor-grab">
        <div class="flex items-center gap-3 truncate">
          <div class={`size-8 rounded-md flex items-center justify-center text-xs font-bold text-white shadow-inner ${props.roleColor}`}>
            {getInitials(props.player!.name)}
          </div>
          <span class="font-medium text-sm text-slate-800 truncate">
            {props.player!.name}
          </span>
        </div>
        <div
          class="size-5 rounded-full flex items-center justify-center shrink-0 transition-colors"
          classList={{
            "bg-green-100 text-green-600": props.player!.isReady,
            "bg-slate-100 text-slate-400": !props.player!.isReady,
          }}
        >
          <Show when={props.player!.isReady} fallback={<FiClock class="size-3" />}>
            <FiCheck class="size-3 stroke-2" />
          </Show>
        </div>
      </div>
    </Show>
  );
};

export const WaitingRoom: Component = () => {
  const params = useParams();
  const [roomData] = createResource(() => params.sessionId, (id) => SessionAPI.fetchWaitingRoom(id));
  const [isLocalPlayerReady, setIsLocalPlayerReady] = createSignal(false);

  return (
    <div class="flex h-full gap-4">
      <Show when={!roomData.loading && roomData()} fallback={<div class="p-4">Loading lobby...</div>}>
        {(data) => (
          <>
            <aside class="w-1/4 min-w-62.5 flex flex-col bg-white border border-slate-200 rounded-md shadow-sm overflow-hidden">
              <div class="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center shrink-0">
                <span class="font-medium uppercase tracking-wider text-slate-600 flex items-center gap-2 text-xs">
                  <FiUsers class="size-4" /> Incoming
                </span>
                <span class="px-2 py-0.5 bg-slate-200 text-slate-600 rounded-full text-[10px] font-bold">
                  {data().incoming.length}
                </span>
              </div>

              <div class="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar bg-slate-50/30">
                <For each={data().incoming}>
                  {(user) => (
                    <div class="flex items-center gap-3 p-2 rounded-md hover:bg-white hover:shadow-sm border border-transparent hover:border-slate-200 cursor-grab transition-all">
                      <div class="size-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-500 shrink-0">
                        {getInitials(user.name)}
                      </div>
                      <span class="font-medium text-sm text-slate-700 truncate">{user.name}</span>
                    </div>
                  )}
                </For>
              </div>
            </aside>

            <section class="flex-1 flex flex-col bg-white border border-slate-200 rounded-md shadow-sm overflow-hidden min-h-0">
              <div class="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center shrink-0">
                <div class="flex items-center gap-3">
                   <div class="size-2 bg-amber-400 rounded-full animate-pulse" />
                   <span class="font-medium uppercase tracking-wider text-slate-600 text-xs">
                     Squad Assembly
                   </span>
                </div>
                <span class="text-xs text-slate-500 font-medium">Session ID: <span class="font-mono text-slate-800">#{data().sessionId}</span></span>
              </div>

              <div class="flex-1 overflow-y-auto p-6 bg-slate-50/50">
                <div class="grid grid-cols-3 gap-8">
                  <div class="flex flex-col gap-4">
                    <div class="flex items-center justify-between border-b border-slate-200 pb-2">
                      <h3 class="font-medium text-slate-700 flex items-center gap-2 text-sm"><FiShield class="text-purple-500" /> Supervisors</h3>
                    </div>
                    <div class="flex flex-col gap-3">
                      <For each={data().supervisors}>{(player) => <PlayerSlot player={player} roleColor="bg-purple-500" />}</For>
                    </div>
                  </div>

                  <div class="flex flex-col gap-4">
                    <div class="flex items-center justify-between border-b border-slate-200 pb-2">
                      <h3 class="font-medium text-slate-700 flex items-center gap-2 text-sm"><FiCpu class="text-blue-500" /> Gamemasters</h3>
                    </div>
                    <div class="flex flex-col gap-3">
                      <For each={data().gamemasters}>{(player) => <PlayerSlot player={player} roleColor="bg-blue-500" />}</For>
                    </div>
                  </div>

                  <div class="flex flex-col gap-4">
                    <div class="flex items-center justify-between border-b border-slate-200 pb-2">
                      <h3 class="font-medium text-slate-700 flex items-center gap-2 text-sm"><FiTarget class="text-amber-500" /> Operators</h3>
                    </div>
                    <div class="flex flex-col gap-3">
                      <For each={data().operators}>{(player) => <PlayerSlot player={player} roleColor="bg-amber-500" />}</For>
                    </div>
                  </div>
                </div>
              </div>

              <div class="p-4 border-t border-slate-200 bg-white flex justify-between items-center shrink-0">
                <button class="px-4 py-2 rounded-md border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium text-sm flex items-center gap-2 transition-colors shadow-sm">
                  <FiMessageSquare class="size-4" /> Open Chat
                </button>
                <button
                  onClick={() => setIsLocalPlayerReady(!isLocalPlayerReady())}
                  class="px-8 py-2 rounded-md font-medium text-sm flex items-center gap-2 transition-all shadow-sm border"
                  classList={{
                    "bg-green-600 hover:bg-green-700 border-green-700 text-white": isLocalPlayerReady(),
                    "bg-blue-600 hover:bg-blue-700 border-blue-700 text-white": !isLocalPlayerReady()
                  }}
                >
                  <Show when={isLocalPlayerReady()} fallback={<><FiCheck class="size-4 opacity-50" /> Ready to Start</>}>
                    <FiCheck class="size-4" /> Cancel Ready
                  </Show>
                </button>
              </div>
            </section>
          </>
        )}
      </Show>
    </div>
  );
};

export default WaitingRoom;
