/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { type Component } from "solid-js";
import { A } from "@solidjs/router";
import { RoleGuard } from "@/features/auth";
import { FiLogIn, FiServer, FiEdit3, FiCommand } from "solid-icons/fi";

const Home: Component = () => {
  return (
    <RoleGuard role="gamemaster" fallback="/join-session">
      <div class="w-full h-full flex flex-col items-center justify-center  p-6 font-sans">
        <div class="w-full max-w-4xl flex flex-col items-center gap-10">
          {/* En-tête du Dashboard */}
          <div class="text-center space-y-3">
            <div class="inline-flex items-center justify-center p-4 bg-blue-100 text-blue-600 rounded-2xl mb-2 shadow-sm border border-blue-200/50">
              <FiCommand class="size-8" />
            </div>
            <h1 class="text-3xl font-bold text-slate-800 tracking-tight">
              Gamemaster Terminal
            </h1>
            <p class="text-slate-500 text-sm font-medium">
              Select an action to manage your active sessions and templates.
            </p>
          </div>

          {/* Cartes d'actions (Grille) */}
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
            {/* Edit Template */}
            <A
              href="/projects"
              class="group flex flex-col bg-white border border-slate-200 rounded-xl p-6 hover:border-blue-400 hover:shadow-md transition-all duration-200 cursor-pointer text-left outline-none"
            >
              <div class="p-3 bg-purple-50 text-purple-600 border border-purple-100 rounded-lg w-fit group-hover:bg-purple-100 transition-colors mb-5">
                <FiEdit3 class="size-6" />
              </div>
              <h2 class="text-lg font-semibold text-slate-800 mb-2 group-hover:text-blue-600 transition-colors">
                Edit Template
              </h2>
              <p class="text-sm text-slate-500 leading-relaxed">
                Create and modify project parameters, group structures, and
                variables.
              </p>
            </A>

            {/* Deploy Session */}
            <A
              href="/deploy-session"
              class="group flex flex-col bg-white border border-slate-200 rounded-xl p-6 hover:border-blue-400 hover:shadow-md transition-all duration-200 cursor-pointer text-left outline-none"
            >
              <div class="p-3 bg-blue-50 text-blue-600 border border-blue-100 rounded-lg w-fit group-hover:bg-blue-100 transition-colors mb-5">
                <FiServer class="size-6" />
              </div>
              <h2 class="text-lg font-semibold text-slate-800 mb-2 group-hover:text-blue-600 transition-colors">
                Deploy Session
              </h2>
              <p class="text-sm text-slate-500 leading-relaxed">
                Launch a new environment instance from your existing project
                templates.
              </p>
            </A>

            {/* Join Session */}
            <A
              href="/join-session"
              class="group flex flex-col bg-white border border-slate-200 rounded-xl p-6 hover:border-blue-400 hover:shadow-md transition-all duration-200 cursor-pointer text-left outline-none"
            >
              <div class="p-3 bg-green-50 text-green-600 border border-green-100 rounded-lg w-fit group-hover:bg-green-100 transition-colors mb-5">
                <FiLogIn class="size-6" />
              </div>
              <h2 class="text-lg font-semibold text-slate-800 mb-2 group-hover:text-blue-600 transition-colors">
                Join Session
              </h2>
              <p class="text-sm text-slate-500 leading-relaxed">
                Connect to an active station lobby and prepare your squad for
                deployment.
              </p>
            </A>
          </div>
        </div>
      </div>
    </RoleGuard>
  );
};

export default Home;
