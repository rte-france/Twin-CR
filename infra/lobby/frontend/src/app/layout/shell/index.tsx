/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import {
  type ParentComponent,
  createSignal,
  Show,
  onCleanup,
  onMount,
} from "solid-js";
import { A, useLocation } from "@solidjs/router";

import { useAuth } from "@/features/auth";

export const Shell: ParentComponent = (props) => {
  const { user, roles, logout, manageAccount } = useAuth();
  const [isOpen, setIsOpen] = createSignal(false);
  let dropdownRef: HTMLDivElement | undefined;
  const location = useLocation();

  const handleClickOutside = (e: MouseEvent) => {
    if (dropdownRef && !dropdownRef.contains(e.target as Node)) {
      setIsOpen(false);
    }
  };

  onMount(() => {
    document.addEventListener("mousedown", handleClickOutside);
  });

  onCleanup(() => {
    document.removeEventListener("mousedown", handleClickOutside);
  });

  const isGamemaster = () => roles().includes("gamemaster");

  const isStep1 = () => location.pathname === "/projects" || location.pathname.startsWith("/workspace");
  const isStep2 = () => location.pathname.startsWith("/deploy-session");
  const isStep3 = () => location.pathname.startsWith("/join-session") || location.pathname.startsWith("/waiting-room");

  return (
    <div class="flex flex-col h-screen w-screen bg-slate-50 text-slate-900 font-sans">
      <header class="relative flex justify-between items-center px-4 py-3 shadow-lg overflow-visible">
        <div
          class="absolute inset-0 z-0"
          style={{ background: "radial-gradient(circle at center, #0a1128 0%, #000000 100%)" }}
        ></div>

        <div
          class="absolute inset-0 z-0 pointer-events-none"
          style={{ background: "radial-gradient(circle at center, transparent 30%, rgba(0, 0, 0, 0.8) 100%)" }}
        ></div>

        <svg
          class="absolute inset-0 w-full h-full pointer-events-none z-0"
          style={{ opacity: 0.25, "mix-blend-mode": "overlay" }}
          xmlns="http://www.w3.org/2000/svg"
        >
          <filter id="headerNoise">
            <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter="url(#headerNoise)" />
        </svg>

        <div class="relative z-10 flex items-center pl-2">
          <a href="/" class="font-extrabold text-2xl text-white tracking-tight drop-shadow-md cursor-pointer hover:opacity-95 transition-opacity">
            TwinEu<span class="text-sky-300">.</span>
          </a>
        </div>

        <div class="hidden md:flex items-center absolute left-1/2 -translate-x-1/2 z-10">
          <Show
            when={isGamemaster()}
            fallback={
              <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/20 text-white shadow-sm backdrop-blur-md">
                <span class="w-2 h-2 rounded-full bg-sky-400 animate-pulse"></span>
                <span class="text-sm font-semibold tracking-wide">Join Session</span>
              </div>
            }
          >
            <nav aria-label="Process Steps" class="flex items-center gap-3">
              <A
                href="/projects"
                class={`flex items-center gap-2 group transition-all cursor-pointer ${
                  isStep1() ? "opacity-100" : "opacity-60 hover:opacity-100"
                }`}
              >
                <span
                  class={`w-6 h-6 rounded-full font-semibold text-xs flex items-center justify-center transition-colors ${
                    isStep1()
                      ? "bg-sky-500/30 border border-sky-400 text-sky-300 shadow-sm shadow-sky-500/20"
                      : "bg-white/10 border border-white/20 text-white/70 group-hover:bg-white/20"
                  }`}
                >
                  1
                </span>
                <span class={`text-sm font-medium ${isStep1() ? "text-white font-semibold" : "text-white/80"}`}>
                  Edit Template
                </span>
              </A>

              <span class="text-white/30 text-sm">-</span>

              <A
                href="/deploy-session"
                class={`flex items-center gap-2 group transition-all cursor-pointer ${
                  isStep2() ? "opacity-100" : "opacity-60 hover:opacity-100"
                }`}
              >
                <span
                  class={`w-6 h-6 rounded-full font-semibold text-xs flex items-center justify-center transition-colors ${
                    isStep2()
                      ? "bg-sky-500/30 border border-sky-400 text-sky-300 shadow-sm shadow-sky-500/20"
                      : "bg-white/10 border border-white/20 text-white/70 group-hover:bg-white/20"
                  }`}
                >
                  2
                </span>
                <span class={`text-sm font-medium ${isStep2() ? "text-white font-semibold" : "text-white/80"}`}>
                  Deploy Session
                </span>
              </A>

              <span class="text-white/30 text-sm">-</span>

              <A
                href="/join-session"
                class={`flex items-center gap-2 group transition-all cursor-pointer ${
                  isStep3() ? "opacity-100" : "opacity-60 hover:opacity-100"
                }`}
              >
                <span
                  class={`w-6 h-6 rounded-full font-semibold text-xs flex items-center justify-center transition-colors ${
                    isStep3()
                      ? "bg-sky-500/30 border border-sky-400 text-sky-300 shadow-sm shadow-sky-500/20"
                      : "bg-white/10 border border-white/20 text-white/70 group-hover:bg-white/20"
                  }`}
                >
                  3
                </span>
                <span class={`text-sm font-medium ${isStep3() ? "text-white font-semibold" : "text-white/80"}`}>
                  Join Session
                </span>
              </A>
            </nav>
          </Show>
        </div>

        <div class="relative z-10 flex items-center gap-6" ref={dropdownRef}>
          <button
            onClick={() => setIsOpen(!isOpen())}
            class="w-10 h-10 rounded-full border border-white/20 flex items-center justify-center bg-white/10 backdrop-blur-md shadow-inner hover:bg-white/20 hover:scale-105 transition-all focus:outline-none focus:ring-2 focus:ring-sky-300 focus:ring-offset-2 focus:ring-offset-blue-900 cursor-pointer"
          >
            <span class="text-sm font-bold text-white">{user().initial}</span>
          </button>

          <Show when={isOpen()}>
            <div class="absolute right-0 top-12 mt-2 w-56 bg-white rounded-xl shadow-2xl py-2 border border-slate-100 flex flex-col z-50 origin-top-right animate-in fade-in slide-in-from-top-2 duration-200">
              <div class="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
                <div class="flex items-center gap-2 mb-1">
                  <p class="text-sm font-semibold text-slate-900">
                    {user().username}
                  </p>
                  <Show when={roles().length > 0}>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-200">
                      {roles().find(r => r === 'gamemaster' || r === 'scada') || roles()[0]}
                    </span>
                  </Show>
                </div>
                <p class="text-xs text-slate-500 truncate">
                  {user().email || "user@twineu.com"}
                </p>
              </div>

              <div class="py-1">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    setIsOpen(false);
                    manageAccount();
                  }}
                  class="w-full flex items-center px-4 py-2 text-sm text-slate-700 hover:bg-sky-50 hover:text-blue-700 transition-colors text-left cursor-pointer"
                >
                  <svg
                    class="w-4 h-4 mr-3 opacity-70"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                  Profile
                </button>

                <button
                  onClick={(e) => {
                    e.preventDefault();
                    setIsOpen(false);
                    manageAccount();
                  }}
                  class="w-full flex items-center px-4 py-2 text-sm text-slate-700 hover:bg-sky-50 hover:text-blue-700 transition-colors text-left cursor-pointer"
                >
                  <svg
                    class="w-4 h-4 mr-3 opacity-70"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                    />
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                  Settings
                </button>
              </div>

              <div class="border-t border-slate-100 pt-1">
                <button
                  onClick={() => {
                    setIsOpen(false);
                    logout();
                  }}
                  class="flex items-center w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors cursor-pointer"
                >
                  <svg
                    class="w-4 h-4 mr-3 opacity-70"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                    />
                  </svg>
                  Logout
                </button>
              </div>
            </div>
          </Show>
        </div>
      </header>

      <main
        class="flex-1 flex flex-col min-h-0 bg-slate-50 relative overflow-auto z-0"
        style={{
          "background-image": "radial-gradient(#cbd5e1 1px, transparent 1px)",
          "background-size": "24px 24px",
        }}
      >
        <div class="z-10 relative h-full flex flex-col">{props.children}</div>
      </main>
    </div>
  );
};
