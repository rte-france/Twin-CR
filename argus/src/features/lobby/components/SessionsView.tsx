/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onCleanup } from "solid-js";
import { Mode } from "@/services/app-mode";
import { GameSession, SessionState } from "@/services/session-manager/types";
import { FiLogIn } from "solid-icons/fi";
import { For } from "solid-js";
import { AccessModal } from "./AccessModal";
import { connectSession, launchSession, parseUtcDate } from "@/services/session-manager";
import { useNavigate } from "@solidjs/router";
import { useAppMode } from "@/hooks/useAppMode";
import { useAuth } from "@/features/auth/hooks/useAuth";
import { Show } from "solid-js";
import { Icon } from "@iconify-icon/solid";

type SessionsViewProps = {
  sessions: GameSession[];
};

export function SessionsView(props: SessionsViewProps) {
  const [showAccessKeyModal, setShowAccessKeyModal] = createSignal(false);
  const [accessKey, setAccessKey] = createSignal("");
  const [accessKeyMode, setAccessKeyMode] = createSignal<Mode | null>(null);
  const [currentSession, setCurrentSession] = createSignal<GameSession | null>(null);
  const [launchingSessions, setLaunchingSessions] = createSignal<Set<number>>(new Set());
  const [launchError, setLaunchError] = createSignal<string | null>(null);
  const [joinError, setJoinError] = createSignal<string | null>(null);

  const navigate = useNavigate();
  const [, setMode] = useAppMode();
  const auth = useAuth();

  const isLaunching = (sessionId: number) => launchingSessions().has(sessionId);

  const setLaunching = (sessionId: number, launching: boolean) => {
    setLaunchingSessions((previous) => {
      const next = new Set(previous);
      if (launching) {
        next.add(sessionId);
      } else {
        next.delete(sessionId);
      }
      return next;
    });
  };

  const openAccessModal = (mode: Mode, session: GameSession) => {
    setAccessKeyMode(mode);
    setCurrentSession(session);
    setAccessKey("");
    setJoinError(null);
    setShowAccessKeyModal(true);
  };

  const handleJoin = async (mode: Mode, session: GameSession, password: string) => {
    await connectSession({
      game_session_id: session.id,
      password_gm: mode === Mode.GameMaster ? password : "",
      password_operator: mode === Mode.Scada ? password : "",
    });

    setMode(mode);
    navigate("/home");
  };

  const [now, setNow] = createSignal(Date.now());

  const interval = setInterval(() => {
    setNow(Date.now());
  }, 5000);

  onCleanup(() => clearInterval(interval));

  function formatElapsed(dateStr: string | null): string {
    if (!dateStr) {
      return "-";
    }
    const elapsedMs = Math.max(0, now() - parseUtcDate(dateStr).getTime());

    const totalSeconds = Math.floor(elapsedMs / 1000);

    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const timePart = [
      hours.toString().padStart(2, "0"),
      minutes.toString().padStart(2, "0"),
      seconds.toString().padStart(2, "0"),
    ].join(":");

    if (days > 0) {
      return `${days} day${days > 1 ? "s" : ""}, ${timePart}`;
    }

    return timePart;
  }

  return (
    <div class="h-full min-h-0 flex flex-col">
      <div class="flex justify-between items-center px-8 py-4 bg-slate-800 border-b border-slate-700">
        <span class="text-sm font-semibold tracking-wide text-slate-200 uppercase">
          Active Sessions
        </span>
      </div>
      {/* ACCESS MODAL */}
      <AccessModal
        open={showAccessKeyModal()}
        mode={accessKeyMode()}
        accessKey={accessKey()}
        error={joinError()}
        onAccessKeyChange={(value) => {
          setJoinError(null);
          setAccessKey(value);
        }}
        onCancel={() => {
          setJoinError(null);
          setShowAccessKeyModal(false);
        }}
        onConfirm={async () => {
          const key = accessKey().trim();
          if (!key) {
            setJoinError("Enter an access key.");
            return;
          }
          setJoinError(null);
          try {
            await handleJoin(accessKeyMode()!, currentSession()!, key);
            setShowAccessKeyModal(false);
          } catch (err) {
            console.error("Connection error to session:", err);
            setJoinError(err instanceof Error ? err.message : String(err));
          }
        }}
      />
      <Show when={launchError()}>
        {(message) => (
          <p class="mx-6 mt-4 border-l-2 border-red-600 bg-red-50 px-3 py-2 text-xs text-red-800">
            {message()}
          </p>
        )}
      </Show>

      {/* SESSIONS LIST */}
      <div class="px-6 py-4 flex-1 min-h-0 overflow-auto">
        <For each={props.sessions}>
          {(session) => (
            <div class="flex items-center justify-between px-6 py-4 gap-6 bg-white border-b border-slate-200 hover:bg-slate-50 transition-colors">
              <div class="flex flex-col justify-center flex-1 min-w-0">
                <span class="text-sm font-semibold text-slate-900 truncate">
                  {session.name}
                </span>
                <span class="text-xs text-slate-500 mt-1">
                  <Icon class="mr-1" icon="lucide:user-round" />
                  Author: {session.author}
                </span>
                <span class="text-xs text-slate-400">
                  <Icon class="mr-1" icon="lucide:file-text" />
                  template : {session.template_name}
                </span>
              </div>

              <div class="flex items-center gap-2 w-24 shrink-0">
                <span
                  class={`w-2 h-2 rounded-full ${
                    session.state === SessionState.Ended
                      ? "bg-red-500"
                      : "bg-green-500"
                  }`}
                />
                <span class="text-xs text-slate-600 font-medium">
                  <Show
                    when={session.state === SessionState.Ongoing}
                    fallback={session.state}
                  >
                    {session.state} for {formatElapsed(session.started_at)}
                  </Show>
                </span>
              </div>

              <div class="flex items-center gap-1.5 w-24 shrink-0">
                <Show when={auth.isSessionLauncher()}>
                  <span>
                    <button
                      disabled={session.state !== SessionState.Ready || isLaunching(session.id)}
                      onClick={async () => {
                        setLaunchError(null);
                        try {
                          setLaunching(session.id, true);
                          await launchSession(session.id);
                        } catch (err) {
                          console.error(err);
                          setLaunchError(
                            err instanceof Error ? err.message : String(err),
                          );
                        } finally {
                          setLaunching(session.id, false);
                        }
                      }}
                      class="px-3 py-1.5 text-xs font-medium border border-slate-300 bg-white text-slate-700 enabled:hover:bg-slate-800 enabled:hover:text-white enabled:hover:border-slate-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <Show
                        when={!isLaunching(session.id)}
                        fallback={<Icon class="mr-1 animate-spin" icon="lucide:loader" />}
                      >
                        <Icon class="mr-1" icon="lucide:play" />
                      </Show>
                      {isLaunching(session.id) ? "Launching..." : "Launch"}
                    </button>
                  </span>
                </Show>
              </div>

              {/* Boutons */}
              <div class="flex flex-col gap-1.5 shrink-0 w-24">
                <button
                  disabled={session.state === SessionState.Ended}
                  onClick={() => openAccessModal(Mode.GameMaster, session)}
                  class="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-800 hover:text-white hover:border-slate-800 transition-colors disabled:opacity-40 disabled"
                >
                  <FiLogIn class="w-2.5 h-2.5 opacity-70" />
                  GM
                </button>

                <button
                  disabled={session.state === SessionState.Ended}
                  onClick={() => openAccessModal(Mode.Scada, session)}
                  class="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-800 hover:text-white hover:border-slate-800 transition-colors disabled:opacity-40 disabled"
                >
                  <FiLogIn class="w-2.5 h-2.5 opacity-70" />
                  SCADA
                </button>
              </div>
            </div>
          )}
        </For>
      </div>
    </div>
  );
}
