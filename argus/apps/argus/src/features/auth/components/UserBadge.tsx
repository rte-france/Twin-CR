/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { DropdownMenu } from "@kobalte/core/dropdown-menu";
import { Show } from "solid-js";

import { useAuth } from "../hooks/useAuth";
import { loginWithKeycloak } from "@/features/auth";
import { getConfigSync } from "@/hooks/useConfig";

const itemClass =
  "flex cursor-default items-center justify-between rounded-sm px-3 py-1.5 outline-none text-fg data-[highlighted]:bg-sidebar-active-bg data-[highlighted]:text-sidebar-active transition-colors";
const separatorClass = "mx-1 my-1.5 h-px bg-divider";
const contentClass =
  "z-50 min-w-[260px] origin-top-right rounded-md border border-popover-border bg-popover-bg p-1.5 text-[12px] text-fg shadow-xl font-sans outline-none animate-in fade-in zoom-in-95 duration-100";

export const UserBadge = () => {
  const { user, tokenParsed, logout, manageAccount } = useAuth();

  const isAuthenticated = () => !!tokenParsed();

  const handleLogin = async (e: Event) => {
    e.preventDefault();
    const config = getConfigSync();
    await loginWithKeycloak({
      ...config,
      keycloakUrl: config.keycloakUrl,
    });
  };

  return (
    <div class="flex items-center gap-1">
      <Show
        when={isAuthenticated()}
        fallback={
          <button
            type="button"
            onClick={handleLogin}
            class="text-xs text-icons hover:text-fg hover:bg-media-bg px-2 py-1 rounded transition-colors cursor-pointer outline-none focus:ring-1 focus:ring-links"
          >
            Sign In
          </button>
        }
      >
        <DropdownMenu>
          <DropdownMenu.Trigger
            class="inline-flex items-center justify-center outline-none focus:outline-none cursor-pointer transition-colors"
            classList={{
              "h-5 w-5 rounded-full bg-sidebar-active-bg border border-sidebar-active/30 text-[10px] font-bold text-links overflow-hidden":
                isAuthenticated(),
              "text-xs text-icons hover:text-fg hover:bg-media-bg p-1 rounded":
                !isAuthenticated(),
            }}
          >
            <Show
              when={isAuthenticated()}
              fallback={
                <svg
                  class="h-3.5 w-3.5 opacity-70"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              }
            >
              <span class="uppercase">{user().initial}</span>
            </Show>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content class={contentClass}>
              <Show when={isAuthenticated()}>
                <div class="px-3 py-1 text-[10px] uppercase font-semibold tracking-wider text-sidebar-non-existant">
                  Profile
                </div>
                <DropdownMenu.Item class={itemClass} onSelect={manageAccount}>
                  <span class="font-medium">{user().username}</span>
                </DropdownMenu.Item>
              </Show>

              <DropdownMenu.Separator class={separatorClass} />

              <Show when={isAuthenticated()}>
                <DropdownMenu.Item
                  class={`${itemClass} hover:text-toast-border-error data-[highlighted]:text-toast-border-error`}
                  onSelect={logout}
                >
                  Sign Out
                </DropdownMenu.Item>
              </Show>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu>
      </Show>
    </div>
  );
};
