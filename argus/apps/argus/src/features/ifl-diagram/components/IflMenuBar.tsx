/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component, createSignal, Show } from "solid-js";
import { FiSearch, FiRefreshCw, FiMenu, FiX } from "solid-icons/fi";
import { useIflContext } from "../hooks/useIflContext";
import { IflMenuEditor } from "./IflMenuEditor";

export const IflMenuBar: Component = () => {
  const ctx = useIflContext();
  const [mobileOpen, setMobileOpen] = createSignal(false);

  const statusDotClass = () => {
    const s = ctx.status();
    if (s === "success") return "bg-[#10b981] shadow-[0_0_5px_#10b981]";
    if (s === "error") return "bg-[#ef4444] shadow-[0_0_5px_#ef4444]";
    if (s === "loading")
      return "bg-[#f59e0b] shadow-[0_0_5px_#f59e0b] animate-pulse";
    return "bg-[var(--border-hover)]";
  };

  const statusLabel = () => {
    const s = ctx.status();
    if (s === "success") return "OK";
    if (s === "error") return "ERR";
    if (s === "loading") return "...";
    return "IDLE";
  };

  const isDisabled = () =>
    ctx.status() === "loading";

  return (
    <div class="flex items-center gap-2 px-3 bg-sidebar-bg border-b border-divider h-9 shrink-0">
      <div class="flex items-center h-full shrink-0">
        <div class="hidden md:block">
          <IflMenuEditor />
        </div>
        <button
          class="md:hidden p-1 hover:bg-[var(--sidebar-active-bg)] rounded transition-colors text-[var(--fg)]"
          onClick={() => setMobileOpen(!mobileOpen())}
        >
          <Show when={mobileOpen()} fallback={<FiMenu size={18} />}>
            <FiX size={18} />
          </Show>
        </button>
      </div>

      <div class="flex-1" />

      <div class="hidden md:flex items-center relative mr-3">
        <FiSearch class="absolute left-2 size-3 text-[var(--fg)] opacity-50 pointer-events-none" />
        <input
          type="text"
          value={ctx.searchQuery()}
          onInput={(e) => ctx.setSearchQuery(e.currentTarget.value)}
          placeholder="Search..."
          class="w-32 lg:w-40 pl-7 pr-2 py-1 text-[11px] font-mono bg-transparent border border-[var(--border)] rounded transition-colors focus:outline-none focus:border-[var(--links)] text-[var(--fg)] placeholder:opacity-40"
        />
      </div>

      <div class="hidden md:block w-px h-4 bg-[var(--border)] mx-1 lg:mx-3" />

      <div class="w-px h-4 bg-[var(--border)] mx-1 lg:mx-3 shrink-0" />

      <div class="flex items-center gap-2 shrink-0">
        <button
          onClick={() => ctx.triggerLoad()}
          disabled={isDisabled()}
          class="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono tracking-widest transition-all duration-200 border bg-transparent text-[var(--fg)] opacity-60 border-[var(--border)] hover:bg-[var(--theme-hover)] hover:opacity-100 disabled:opacity-30"
        >
          <FiRefreshCw
            class={`size-3 ${ctx.status() === "loading" ? "animate-spin" : ""}`}
          />
          <span class="hidden xs:inline">REFRESH</span>
        </button>

        <div
          class="flex items-center gap-1.5 ml-1"
          title={`Status: ${ctx.errorMessage() ?? ctx.status()}`}
        >
          <span
            class={`w-1.5 h-1.5 rounded-full shrink-0 ${statusDotClass()}`}
          />
          <span class="hidden sm:inline text-[10px] tracking-wider font-mono opacity-60 uppercase">
            {statusLabel()}
          </span>
        </div>
      </div>

      <Show when={mobileOpen()}>
        <div class="absolute top-9 left-0 w-full bg-[var(--popover-bg)] border-b border-[var(--border)] shadow-xl flex flex-col p-3 gap-4 z-50 md:hidden animate-in slide-in-from-top-1 duration-200">
          <div class="flex flex-col gap-2">
            <span class="text-[9px] font-bold opacity-40 tracking-[0.2em] uppercase px-1">
              Menu
            </span>
            <IflMenuEditor />
          </div>

          <div class="flex flex-col gap-3 border-t border-[var(--border)] pt-3">
            <span class="text-[9px] font-bold opacity-40 tracking-[0.2em] uppercase px-1">
              Search & Network
            </span>
            <div class="relative">
              <FiSearch class="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-[var(--fg)] opacity-50" />
              <input
                type="text"
                value={ctx.searchQuery()}
                onInput={(e) => ctx.setSearchQuery(e.currentTarget.value)}
                placeholder="Search..."
                class="w-full pl-8 pr-2 py-2 text-[11px] font-mono bg-[var(--pre-bg)] border border-[var(--border)] rounded outline-none focus:border-[var(--links)]"
              />
            </div>
          </div>
        </div>
      </Show>
    </div>
  );
};
