/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, createSignal, Show } from "solid-js";
import { useNavigate } from "@solidjs/router";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { FiX, FiServer, FiLogIn, FiAlertCircle } from "solid-icons/fi";

import { accessToken, authError, loginWithKeycloak } from "@/features/auth";
import { getConfigSync, setCustomKeycloakUrl } from "@/hooks/useConfig";

export const SignIn = () => {
  const appWindow = getCurrentWindow();
  const config = getConfigSync();
  const navigate = useNavigate();

  const [authUrl, setAuthUrl] = createSignal<string>(config.keycloakUrl);
  // Token held when the browser login was started; undefined when not waiting.
  // Only leave this page once a new token arrives, so a wrong URL leaves the
  // user here to correct it instead of in a lobby with no way back.
  const [waitingFrom, setWaitingFrom] = createSignal<string | null | undefined>(
    undefined,
  );

  createEffect(() => {
    const from = waitingFrom();
    if (from === undefined) return;
    if (authError()) {
      setWaitingFrom(undefined);
    } else if (accessToken() && accessToken() !== from) {
      setWaitingFrom(undefined);
      navigate("/lobby");
    }
  });

  const close = () => appWindow.close();

  const handleLogin = async (e: Event) => {
    e.preventDefault();

    const customUrl = authUrl();
    setCustomKeycloakUrl(customUrl);

    await loginWithKeycloak({
      ...config,
      keycloakUrl: customUrl,
    });

    if (!authError()) {
      setWaitingFrom(accessToken());
    }
  };

  const handleLocalMode = (e: Event) => {
    e.preventDefault();
    navigate("/home");
  };

  return (
    <div class="flex flex-col h-screen overflow-hidden select-none font-sans">
      <div
        data-tauri-drag-region
        class="h-10 flex items-center justify-between px-4 bg-[var(--sidebar-bg)] border-b border-[var(--border-light)] z-50"
      >
        <h1 class="text-sm font-medium">Twin-CR</h1>
        <button
          onClick={close}
          class="w-7 h-7 flex items-center justify-center rounded-md hover:bg-red-500/20 hover:text-red-500 transition-all group"
        >
          <FiX class="w-4 h-4 group-active:scale-95" />
        </button>
      </div>

      <div class="relative flex-1 bg-[var(--bg)] text-[var(--fg)] transition-colors duration-300">
        <div
          class="absolute inset-0 pointer-events-none"
          style={{
            "background-image":
              "radial-gradient(color-mix(in srgb, var(--sidebar-active), transparent 80%) 2px, transparent 2px)",
            "background-size": "32px 32px",
            "mask-image":
              "radial-gradient(circle at center, black 40%, transparent 95%)",
            "-webkit-mask-image":
              "radial-gradient(circle at center, black 40%, transparent 95%)",
          }}
        />

        <div class="relative z-10 h-full flex flex-col items-center justify-center p-8">
          <div class="flex flex-col items-center gap-12 animate-in fade-in slide-in-from-bottom-8 duration-700 w-full max-w-sm">
            <div class="flex flex-col items-center space-y-6">
              <div class="text-center">
                <h2
                  class="text-3xl font-bold tracking-tighter uppercase italic opacity-90"
                  style={{
                    color: "var(--title-color)",
                    "font-family": "var(--title-font)",
                  }}
                >
                  Idenfication
                </h2>
                <p class="text-[10px] font-mono uppercase tracking-[0.4em] opacity-40 italic mt-2">
                  Need some authentification
                </p>
              </div>
            </div>

            <form onSubmit={handleLogin} class="w-full flex flex-col gap-6">
              <Show when={authError()}>
                {(error) => (
                  <div class="flex items-center gap-2 p-3 text-xs rounded-lg border border-[var(--toast-border-error)] bg-[var(--toast-bg)] text-[var(--toast-border-error)]">
                    <FiAlertCircle class="w-4 h-4 shrink-0" />
                    <span class="break-words">{error()}</span>
                  </div>
                )}
              </Show>

              <div class="flex flex-col gap-2">
                <label class="text-[10px] font-mono uppercase tracking-widest opacity-60 ml-1">
                  Authentification Server
                </label>
                <div class="relative flex items-center group">
                  <div class="absolute left-4 text-[var(--links)] opacity-70 group-focus-within:opacity-100 transition-opacity">
                    <FiServer class="w-5 h-5" />
                  </div>
                  <input
                    type="url"
                    required
                    value={authUrl()}
                    onInput={(e) => setAuthUrl(e.currentTarget.value)}
                    class="w-full bg-[var(--sidebar-bg)] border border-[var(--border-light)] rounded-xl py-4 pl-12 pr-4 text-sm focus:outline-none focus:border-[var(--links)] transition-all placeholder-opacity-30"
                    placeholder={config.keycloakUrl}
                  />
                </div>
              </div>

              <div class="flex flex-col items-center gap-4 mt-2">
                <button
                  type="submit"
                  class="group relative flex items-center justify-center gap-3 p-4 w-full rounded-xl bg-[var(--links)] text-[var(--bg)] shadow-lg shadow-[var(--links)]/20 transition-all hover:-translate-y-1 outline-none focus-visible:ring-2 focus-visible:ring-white"
                >
                  <span class="text-sm font-bold uppercase tracking-wide">
                    <Show when={waitingFrom() !== undefined} fallback="Login">
                      Waiting for browser login…
                    </Show>
                  </span>
                  <FiLogIn class="w-5 h-5 transition-transform group-hover:translate-x-1" />
                </button>

                <button
                  type="button"
                  onClick={handleLocalMode}
                  class="text-xs font-medium opacity-60 hover:opacity-100 hover:text-[var(--links)] transition-colors underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--links)] rounded px-2 py-1"
                >
                  Continue in local mode
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
