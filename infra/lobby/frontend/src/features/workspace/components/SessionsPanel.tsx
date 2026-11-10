/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import {
  FiPlay,
  FiRefreshCw,
  FiServer,
  FiSquare,
  FiStopCircle,
} from "solid-icons/fi";
import { type Component, For, Show } from "solid-js";
import type { LobbyStore } from "@/features/workspace/hooks/store";
import type { PreparedSession } from "../types";

function statusColors(status: string): string {
  if (status === "RUNNING") return "bg-green-100 text-green-800";
  if (status === "STOPPED") return "bg-red-100 text-red-800";
  return "bg-indigo-100 text-indigo-800";
}

const SessionsPanel: Component<{ store: LobbyStore }> = (props) => {
  return (
    <aside class="col-start-3 row-start-2 flex flex-col p-3 border-l border-gray-200 bg-gray-50 h-full overflow-hidden">
      <div class="flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <div class="flex items-center justify-between px-3 py-2.5 font-semibold text-gray-700 bg-gray-50 border-b border-gray-200">
          <div class="flex items-center gap-2">
            <FiServer class="text-green-600" />
            Prepared Sessions
          </div>
          <button
            class="p-1 text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            title="Refresh"
            onClick={() => props.store.loadSessions()}
          >
            <FiRefreshCw class="text-sm" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto">
          <Show
            when={props.store.preparedSessions().length > 0}
            fallback={
              <div class="p-5 text-center text-xs text-gray-400 italic">
                No sessions found.
                <br />
                Click "Prepare Session" to load one.
              </div>
            }
          >
            <For each={props.store.preparedSessions()}>
              {(sess: PreparedSession) => (
                <div class="flex flex-col gap-2 p-3 border-b border-gray-100 hover:bg-gray-50/50 transition-colors">
                  <div class="flex justify-between items-start">
                    <div class="font-semibold text-[13px] text-gray-800 break-all">
                      {sess.name}
                    </div>
                    <span
                      class={`px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0 ${statusColors(sess.status)}`}
                    >
                      {sess.status}
                    </span>
                  </div>
                  <div class="text-[10px] text-gray-500 font-mono break-all">
                    {sess.id}
                  </div>

                  <div class="flex gap-2 mt-1">
                    <Show when={sess.status === "STOPPED"}>
                      <button
                        type="button"
                        class="flex-1 flex justify-center items-center gap-1.5 px-2 py-1 text-xs font-medium text-gray-400 bg-gray-100 border border-gray-200 rounded cursor-not-allowed"
                        disabled
                      >
                        <FiStopCircle class="text-sm" />
                        Stopped
                      </button>
                    </Show>
                    <Show when={sess.status === "RUNNING"}>
                      <button
                        type="button"
                        class="flex-1 flex justify-center items-center gap-1.5 px-2 py-1 text-xs font-medium text-white bg-red-600 border border-red-600 rounded hover:bg-red-700 transition-colors"
                        onClick={() => props.store.stopSession(sess.id)}
                      >
                        <FiSquare class="text-sm" />
                        Stop
                      </button>
                    </Show>
                    <Show
                      when={
                        sess.status !== "RUNNING" && sess.status !== "STOPPED"
                      }
                    >
                      <button
                        type="button"
                        class="flex-1 flex justify-center items-center gap-1.5 px-2 py-1 text-xs font-medium text-white bg-green-600 border border-green-600 rounded hover:bg-green-700 transition-colors"
                        onClick={() => props.store.runSession(sess.id)}
                      >
                        <FiPlay class="text-sm" />
                        Start
                      </button>
                    </Show>
                  </div>
                </div>
              )}
            </For>
          </Show>
        </div>
      </div>
    </aside>
  );
};

export default SessionsPanel;
