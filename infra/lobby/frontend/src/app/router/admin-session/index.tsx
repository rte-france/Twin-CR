/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { type Component, For } from "solid-js";

const AdminSession: Component = () => {
  const incomingUsers = ["User a", "User b", "User c"];

  return (
    <div class="flex flex-col h-screen w-screen bg-white text-gray-900 font-sans p-2 box-border gap-2">
      {/* Header */}
      <header class="flex justify-end items-center p-4 border-2 border-gray-800 bg-white">
        <div class="flex items-center gap-3">
          <span class="font-bold text-lg">User</span>
          <div class="w-10 h-10 rounded-full border-2 border-gray-800 flex items-center justify-center bg-gray-100"></div>
        </div>
      </header>

      {/* Main Content */}
      <main class="flex-1 border-2 border-gray-800 bg-white p-6 flex flex-col justify-between min-h-0">

        {/* Grille des rôles (4 colonnes) */}
        <div class="grid grid-cols-4 gap-6 h-full mb-6">

          {/* Incoming */}
          <div class="flex flex-col items-center">
            <h2 class="font-bold mb-4">Incoming</h2>
            <div class="border-2 border-gray-800 w-full p-4 flex flex-col gap-4 flex-1">
              <For each={incomingUsers}>
                {(user) => (
                  <div class="flex items-center gap-3">
                    <div class="w-6 h-6 rounded-full border-2 border-gray-800"></div>
                    <span class="font-medium">{user}</span>
                  </div>
                )}
              </For>
            </div>
          </div>

          {/* Supervisors */}
          <div class="flex flex-col items-center">
            <h2 class="font-bold mb-4">Supervisors</h2>
            <div class="border-2 border-gray-800 w-16 h-32 mb-4 flex justify-center py-2">
              <div class="w-8 h-8 rounded-full border-2 border-gray-800"></div>
            </div>
            <button class="border-2 border-gray-800 px-4 py-1 font-bold text-sm shadow-[2px_2px_0px_0px_rgba(31,41,55,1)]">Start My</button>
          </div>

          {/* Gamemasters */}
          <div class="flex flex-col items-center">
            <h2 class="font-bold mb-4">Gamemasters</h2>
            <div class="border-2 border-gray-800 w-16 h-48 mb-4 flex flex-col items-center gap-2 py-2">
              <div class="w-8 h-8 rounded-full border-2 border-gray-800"></div>
              <div class="w-8 h-8 rounded-full border-2 border-gray-800"></div>
            </div>
            <button class="border-2 border-gray-800 px-4 py-1 font-bold text-sm shadow-[2px_2px_0px_0px_rgba(31,41,55,1)]">Start My</button>
          </div>

          {/* Operators */}
          <div class="flex flex-col items-center">
            <h2 class="font-bold mb-4">Operators</h2>
            <div class="border-2 border-gray-800 w-16 h-64 mb-4 flex flex-col items-center gap-2 py-2">
              <div class="w-8 h-8 rounded-full border-2 border-gray-800"></div>
              <div class="w-8 h-8 rounded-full border-2 border-gray-800"></div>
              <div class="w-8 h-8 rounded-full border-2 border-gray-800"></div>
            </div>
            <button class="border-2 border-gray-800 px-4 py-1 font-bold text-sm shadow-[2px_2px_0px_0px_rgba(31,41,55,1)]">Start</button>
          </div>

        </div>

        {/* Bottom Actions */}
        <div class="flex justify-between mt-auto">
          <button class="border-2 border-gray-800 bg-white px-8 py-2 font-bold shadow-[2px_2px_0px_0px_rgba(31,41,55,1)] hover:translate-y-[1px] hover:translate-x-[1px] hover:shadow-[1px_1px_0px_0px_rgba(31,41,55,1)]">
            Chat
          </button>
          <button class="border-2 border-gray-800 bg-white px-8 py-2 font-bold shadow-[2px_2px_0px_0px_rgba(31,41,55,1)] hover:translate-y-[1px] hover:translate-x-[1px] hover:shadow-[1px_1px_0px_0px_rgba(31,41,55,1)]">
            Start
          </button>
        </div>
      </main>
    </div>
  );
};

export default AdminSession;
