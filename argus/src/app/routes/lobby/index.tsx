/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, onCleanup, Switch, Show } from "solid-js";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { FiX } from "solid-icons/fi";
import { Effect } from "effect";

import { systemRuntime } from "@/config/runtime";
import { GameSession } from "@/services/session-manager/types";
import {getSessions, initUserTree} from "@/services/session-manager/service";

import { SessionsView } from "@/features/lobby/components/SessionsView";
import { Match } from "solid-js";
import {
  BackgroundLogo,
  ErrorPanel,
  TemplateView,
  errorMessage,
} from "@/features/lobby";
import { MySessionsView } from "@/features/lobby/components/MySessionsView";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { useNavigate } from "@solidjs/router";
import { useAppMode } from "@/hooks/useAppMode";
import { Mode } from "@/services/app-mode";
import { LobbyStatus } from "@/features/lobby-settings";
import { UserBadge } from "@/features/auth";

type View = "SESSIONS" | "TEMPLATES" | "MY_SESSIONS";

export const Lobby = () => {
  const appWindow = getCurrentWindow();
  const close = () => appWindow.close();

  const [view, setView] = createSignal<View>("SESSIONS");

  const [isFetching, setIsFetching] = createSignal(true);
  const [sessions, setSessions] = createSignal<GameSession[]>([]);
  const [error, setError] = createSignal<string | null>(null);

  const auth = useAuth();

  createEffect(() => {
    if (!auth.isAuthenticated()) {
      return;
    }

    void (async () => {
      if (auth.isTemplateManager() || auth.isSessionLauncher()) {
        initUserTree().catch((err) => setError(errorMessage(err)));
      }

      const fetchActiveSession = Effect.gen(function* () {
        const availableSessions = yield* Effect.promise(() => getSessions());
        if (JSON.stringify(availableSessions) !== JSON.stringify(sessions())) {
          setSessions(availableSessions);
        }
        setError(null);
      });

      const refreshSessions = () =>
        systemRuntime
          .runPromise(fetchActiveSession)
          .catch((err) => setError(errorMessage(err)));

      refreshSessions().finally(() => setIsFetching(false));

      const interval = setInterval(() => {
        if (view() !== "SESSIONS") return;
        void refreshSessions();
      }, 5000);

      onCleanup(() => clearInterval(interval));
    })();
  });

  const navigate = useNavigate();
  const [, setMode] = useAppMode();

  return (
    <div class="font-sans w-full h-screen flex bg-slate-100 text-slate-800 overflow-hidden">
      {/* MAIN */}
      <div class="relative flex-1 flex flex-col min-h-0">
        {/* HEADER */}
        <div
          data-tauri-drag-region
          class="flex justify-between items-center px-8 py-4 bg-slate-900 border-b border-slate-700 shadow-lg"
        >
          <span class="text-2xl font-bold tracking-tight text-white">
            Twin-CR.
          </span>

          {/* Buttons */}
          <Show when={auth.isAuthenticated()}>
            <div class="flex items-center">
              <Show when={auth.isTemplateManager() || auth.isSessionLauncher()}>
                <button
                  class={`px-5 py-3 text-sm font-medium transition-colors
                    ${
                      view() === "SESSIONS"
                        ? "text-white border-b-2 border-sky-500"
                        : "text-slate-400 border-b-2 border-transparent hover:text-white"
                    }`}
                  onClick={() => setView("SESSIONS")}
                >
                  Active sessions
                </button>
              </Show>
              <Show when={auth.isTemplateManager()}>
                <button
                  class={`px-5 py-3 text-sm font-medium transition-colors
                    ${
                      view() === "TEMPLATES"
                        ? "text-white border-b-2 border-sky-500"
                        : "text-slate-400 border-b-2 border-transparent hover:text-white"
                    }`}
                  onClick={() => setView("TEMPLATES")}
                >
                  Templates
                </button>
              </Show>
              <Show when={auth.isSessionLauncher()}>
                <button
                  class={`px-5 py-3 text-sm font-medium transition-colors
                    ${
                      view() === "MY_SESSIONS"
                        ? "text-white border-b-2 border-sky-500"
                        : "text-slate-400 border-b-2 border-transparent hover:text-white"
                    }`}
                  onClick={() => setView("MY_SESSIONS")}
                >
                  My sessions
                </button>
              </Show>
            </div>
          </Show>

          <div class="flex items-center gap-4">
            <div class="flex items-center gap-2 text-slate-300">
              <UserBadge />
            </div>

            <button
              onClick={() => close()}
              class="w-9 h-9 flex items-center justify-center text-slate-400 hover:bg-red-500 hover:text-white transition-colors"
            >
              <FiX class="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* CONTENT */}
        <div class="relative flex-1 flex flex-col min-h-0 bg-slate-50">
          <BackgroundLogo />
          <Show when={auth.isAuthenticated()}>
            <div class="relative z-10 flex-1 min-h-0">
              <ErrorPanel message={error()} class="mx-6 mt-4" />
              <Switch>
                <Match when={view() === "SESSIONS" && !isFetching()}>
                  <SessionsView sessions={sessions()} />
                </Match>

                <Match when={view() === "TEMPLATES"}>
                  <TemplateView />
                </Match>

                <Match when={view() === "MY_SESSIONS"}>
                  <MySessionsView />
                </Match>
              </Switch>
            </div>
          </Show>
        </div>
        {/* FOOTER */}
        <div class="mt-auto flex justify-between items-center px-6 py-3 border-t border-slate-200 bg-white">
          <button
            class="px-1 py-0.5 text-xs bg-gray-500 hover:bg-gray-400 text-white"
            onClick={() => {
              setMode(Mode.GameMaster);
              navigate("/home");
            }}
          >
            Local dev session
          </button>
          <span class="text-sm text-slate-400 font-medium">v{import.meta.env.APP_VERSION}</span>
          <LobbyStatus />
        </div>
      </div>
    </div>
  );
};
