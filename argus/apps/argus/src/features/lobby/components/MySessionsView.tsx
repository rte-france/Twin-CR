/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { deleteSession, getMySessions, parseUtcDate, stopSession } from "@/services/session-manager";
import { GameSession, SessionState } from "@/services/session-manager/types";
import { For, Show } from "solid-js";
import { createSignal, onCleanup, onMount } from "solid-js";
import { Icon } from "@iconify-icon/solid";
import { AccessKeysModal } from "./AccessKeysModal";

export function MySessionsView() {
  const [readySessions, setReadySessions] = createSignal<GameSession[]>();
  const [notReadySessions, setNotReadySessions] = createSignal<GameSession[]>();
  const [showKeysModal, setShowKeysModal] = createSignal(false);
  const [selectedSessionId, setSelectedSessionId] = createSignal<number | null>(null);
  const [selectedSessionName, setSelectedSessionName] = createSignal<string | null>(null);
  const [error, setError] = createSignal<string | null>(null);

  const loadSessions = async () => {
    const sessions = await getMySessions();
    const readySessions: GameSession[] = [];
    const otherSessions: GameSession[] = [];

    for (const session of sessions) {
      if (session.state !== SessionState.Ended) {
        readySessions.push(session);
      } else {
        otherSessions.push(session);
      }
    }
    setReadySessions(readySessions);
    setNotReadySessions(otherSessions);
  };

  onMount(() => {
    loadSessions().catch((err) => console.error("Could not load sessions", err));

    const interval = setInterval(() => {
      loadSessions().catch(() => {});
    }, 5000);

    onCleanup(() => clearInterval(interval));
  });

  const removeSession = async (id: number) => {
    const previous = notReadySessions() ?? [];
    setError(null);
    setNotReadySessions(previous.filter((session) => session.id !== id));
    try {
      await deleteSession(id);
    } catch (err) {
      setNotReadySessions(previous);
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div class="h-full min-h-0 flex flex-col p-4">
      {/* Mounted only while open, so every reopen refetches the keys rather
          than showing the copy held since last time. */}
      <Show when={showKeysModal() ? selectedSessionId() : null} keyed>
        {(sessionId) => (
          <AccessKeysModal
            sessionId={sessionId}
            sessionName={selectedSessionName()!}
            onClose={() => setShowKeysModal(false)}
          />
        )}
      </Show>
      <Show when={error()}>
        {(message) => (
          <p class="mb-2 border-l-2 border-red-600 bg-red-50 px-3 py-2 text-xs text-red-800">
            {message()}
          </p>
        )}
      </Show>
      <div class="flex items-center px-2 py-3 border-b border-slate-300">
        <h2 class="text-xs font-semibold tracking-widest uppercase text-slate-600">
          Active Sessions
        </h2>
      </div>
      <div class="flex-1 min-h-0 overflow-y-auto">
        <For each={readySessions()}>
          {(session) => (
            <div class="bg-white border-b border-slate-200 px-6 py-4 hover:bg-slate-50 transition-colors">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                  <h3 class="text-sm font-semibold text-slate-900">
                    {session.name ?? ""}
                  </h3>
                </div>

                <div class="flex items-center gap-4">
                  <span
                    class={`text-xs font-medium text-slate-600 px-1 ${
                      session.state === SessionState.Ended
                        ? "bg-red-100 text-red-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {session.state}
                  </span>

                  <span class="text-xs text-slate-400">
                    #{session.id}
                  </span>
                </div>
              </div>

              <div class="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate">
                <span>Author: {session.author ?? "-"}</span>
                <span>Template: {session.template_name ?? "-"}</span>
                <span>
                  Started: {session.started_at
                    ? parseUtcDate(session.started_at).toLocaleString()
                    : "-"}
                </span>
                <span>
                  Ended: {session.ended_at
                    ? parseUtcDate(session.ended_at).toLocaleString()
                    : "-"}
                </span>
              </div>

              <hr class="my-3 border-slate-200" />

              <div class="flex items-center gap-4">
                <button
                  class="px-3 py-1.5 text-xs font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-800 hover:text-white hover:border-slate-800 transition-colors"
                  onClick={() => {
                    setSelectedSessionId(session.id);
                    setSelectedSessionName(session.name);
                    setShowKeysModal(true);
                  }}
                >
                  <Icon class="mr-1" icon="lucide:key" />
                  Access keys
                </button>

                <button
                  class="px-3 py-1.5 text-xs font-medium border border-red-700 bg-red-700 text-white hover:bg-red-800 transition-colors flex items-center"
                  onClick={async () => {
                    const updatedSession = await stopSession(session.id);

                    setReadySessions(
                      (readySessions() ?? []).filter((s) => s.id !== session.id)
                    );

                    setNotReadySessions([
                      ...(notReadySessions() ?? []),
                      updatedSession,
                    ]);
                  }}
                >
                  <Icon class="mr-1" icon="lucide:square" />
                  Stop session
                </button>
              </div>
            </div>
          )}
        </For>
        <div class="flex items-center px-2 py-3 border-b border-slate-300">
          <h2 class="text-xs font-semibold tracking-widest uppercase text-slate-600">
            Stopped Sessions
          </h2>
        </div>
        <For each={notReadySessions()}>
          {(session) => (
            <div class="bg-white border-b border-slate-200 px-6 py-4 hover:bg-slate-50 transition-colors">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                  <h3 class="text-sm font-semibold text-slate-900">
                    {session.name ?? ""}
                  </h3>
                </div>

                <div class="flex items-center gap-4">
                  <span
                    class={`text-xs font-medium text-slate-600 px-1 ${
                      session.state === SessionState.Ended
                        ? "bg-red-100 text-red-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {session.state}
                  </span>

                  <span class="text-sm text-gray-500">#{session.id}</span>
                </div>
              </div>

              <div class="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate">
                <span>Author: {session.author ?? "-"}</span>
                <span>Template: {session.template_name ?? "-"}</span>
                <span>
                  Started: {session.started_at
                    ? parseUtcDate(session.started_at).toLocaleString()
                    : "-"}
                </span>
                <span>
                  Ended: {session.ended_at
                    ? parseUtcDate(session.ended_at).toLocaleString()
                    : "-"}
                </span>
              </div>

              <hr class="my-2 border-gray-200" />

              <div class="flex items-center gap-2">
                <button
                  class="px-2 py-1.5 border border-red-700 bg-red-700 text-white hover:bg-red-800 transition-colors flex"
                  onClick={() => removeSession(session.id) }
                >
                  <Icon icon="lucide:trash" />
                </button>
              </div>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
