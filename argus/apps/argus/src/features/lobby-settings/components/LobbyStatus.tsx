/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, Show, on } from "solid-js";
import { DropdownMenu } from "@kobalte/core/dropdown-menu";
import {
  TbCircle,
  TbPlug,
  TbPlugX,
  TbRefresh,
  TbLoader,
  TbCheck,
  TbX,
  TbPencil,
  TbAlertCircle,
} from "solid-icons/tb";

import { useLobbyUrl } from "../hooks/useLobbyUrl";

const DEFAULT_URL = "http://localhost:8080";

export const LobbyStatus = () => {
  const { url, serverStatus, loading, error, setUrl, refetch } = useLobbyUrl();

  const [isEditing, setIsEditing] = createSignal(false);
  const [urlInput, setUrlInput] = createSignal(url() || DEFAULT_URL);

  let inputRef: HTMLInputElement | undefined;

  createEffect(
    on(url, (newUrl) => {
      if (!isEditing()) {
        setUrlInput(newUrl || DEFAULT_URL);
      }
    }),
  );

  const isTransitioning = () => loading();
  const actionError = () => error()?.message;

  const status = () => {
    if (actionError()) return "error";
    if (isTransitioning()) return "connecting";

    const s = serverStatus();

    if (s === "Healthy") return "connected";
    if (s === "Connecting") return "connecting";
    if (typeof s === "object" && "Degraded" in s) return "error";

    return "disconnected";
  };

  const getThemeStatusColor = () => {
    const s = status();
    if (s === "connected") return "text-(--toast-border-success)";
    if (s === "connecting") return "text-(--warning-icon)";
    return "text-(--toast-border-error)";
  };

  const getFooterStatusColor = () => {
    const s = status();
    if (s === "connected") return "text-green-500 dark:text-green-400";
    if (s === "connecting") return "text-yellow-500 dark:text-yellow-400";
    if (s === "error") return "text-red-500 dark:text-red-400";
    return "text-(--icons)";
  };

  const getStatusLabel = () => {
    if (actionError()) return "Error";
    switch (status()) {
      case "connected":
        return "Connected";
      case "connecting":
        return "Connecting...";
      case "disconnected":
        return "Disconnected";
      default:
        return "Disconnected";
    }
  };

  const getShortStatusLabel = () => {
    if (actionError()) return "Err";
    switch (status()) {
      case "connected":
        return "On";
      case "connecting":
        return "...";
      case "disconnected":
        return "Off";
      default:
        return "Off";
    }
  };

  const handleStartEditing = () => {
    setUrlInput(url() || DEFAULT_URL);
    setIsEditing(true);
    setTimeout(() => inputRef?.focus(), 10);
  };

  const handleCancelEditing = () => {
    setUrlInput(url() || DEFAULT_URL);
    setIsEditing(false);
  };

  const handleSaveUrl = () => {
    const newUrl = urlInput();
    setUrl(newUrl);
    setIsEditing(false);
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter") handleSaveUrl();
    else if (e.key === "Escape") handleCancelEditing();
  };

  return (
    <DropdownMenu>
      <DropdownMenu.Trigger
        class="group flex cursor-pointer items-center gap-x-1.5 bg-transparent px-1.5 text-[10px] outline-none sm:gap-x-2 sm:px-2"
        title={actionError() ?? `Lobby ${getStatusLabel()}`}
      >
        <Show
          when={!isTransitioning()}
          fallback={<TbLoader class="text-(--icons) size-3 animate-spin" />}
        >
          <Show
            when={!actionError()}
            fallback={
              <TbAlertCircle class={`size-3 ${getFooterStatusColor()}`} />
            }
          >
            <TbCircle class={`size-2 fill-current ${getFooterStatusColor()}`} />
          </Show>
        </Show>

        <span
          class={`hidden xs:inline sm:hidden ${actionError() ? "text-(--toast-border-error)" : "text-(--sidebar-fg)"}`}
        >
          {getShortStatusLabel()}
        </span>
        <span
          class={`hidden sm:inline md:hidden ${actionError() ? "text-(--toast-border-error)" : "text-(--sidebar-fg)"}`}
        >
          {getStatusLabel()}
        </span>
        <span class="text-(--sidebar-fg) font-bold tracking-wide">Lobby</span>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content class="bg-(--popover-bg) border-(--popover-border) text-(--fg) z-50 min-w-[280px] animate-in fade-in-0 zoom-in-95 rounded-md border p-1 shadow-lg outline-none sm:min-w-[300px]">
          <div class="px-2 py-1.5">
            <div class="flex items-center gap-x-2 text-sm font-medium">
              <TbCircle
                class={`size-2 fill-current ${getThemeStatusColor()}`}
              />
              <span class="text-(--title-color) font-title">
                Lobby {getStatusLabel()}
              </span>
            </div>

            <Show when={actionError()}>
              <p class="text-(--toast-border-error) mt-1 wrap-break-word text-xs">
                {actionError()}
              </p>
            </Show>

            <Show when={isTransitioning() && !actionError()}>
              <p class="text-(--icons) mt-1 text-xs">
                Establishing connection...
              </p>
            </Show>
          </div>

          <hr class="bg-(--divider) my-1 h-px border-0" />

          <div class="px-2 py-2">
            <label class="text-(--icons) text-xs font-medium">Server URL</label>

            <Show
              when={isEditing()}
              fallback={
                <div class="mt-1 flex items-center justify-between gap-x-2">
                  <p
                    class="text-(--fg) min-w-0 truncate text-xs"
                    title={urlInput() || DEFAULT_URL}
                  >
                    {urlInput() || DEFAULT_URL}
                  </p>
                  <button
                    onClick={handleStartEditing}
                    disabled={isTransitioning()}
                    class="hover:bg-(--theme-hover) shrink-0 rounded p-1 transition-colors disabled:opacity-50"
                    title="Edit URL"
                  >
                    <TbPencil class="text-(--icons) size-3" />
                  </button>
                </div>
              }
            >
              <div
                class="mt-1 flex items-center gap-x-1"
                onKeyDown={(e) => e.stopPropagation()}
                onKeyUp={(e) => e.stopPropagation()}
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={urlInput()}
                  onInput={(e) => setUrlInput(e.currentTarget.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={DEFAULT_URL}
                  disabled={isTransitioning()}
                  class="border-border bg-bg) text-fg focus:border-sidebar-active h-7 min-w-0 flex-1 rounded-sm border px-2 text-xs transition-colors outline-none"
                />
                <button
                  onClick={handleSaveUrl}
                  disabled={isTransitioning()}
                  class="hover:bg-(--theme-hover) shrink-0 rounded p-1 transition-colors disabled:opacity-50"
                  title="Save & Connect"
                >
                  <TbCheck class="text-(--toast-border-success) size-4" />
                </button>
                <button
                  onClick={handleCancelEditing}
                  class="hover:bg-(--theme-hover) shrink-0 rounded p-1 transition-colors"
                  title="Cancel"
                >
                  <TbX class="text-(--icons) size-4" />
                </button>
              </div>
            </Show>
          </div>

          <hr class="bg-(--divider) my-1 h-px border-0" />

          <Show when={status() === "disconnected" || status() === "error"}>
            <DropdownMenu.Item
              onSelect={() => setUrl(urlInput())}
              disabled={isTransitioning()}
              class="hover:bg-(--theme-hover) data-disabled:opacity-50 flex cursor-pointer items-center rounded-sm px-2 py-1.5 text-xs transition-colors outline-none"
            >
              <TbPlug class="text-(--icons) mr-2 size-4" />
              <span>Connect</span>
            </DropdownMenu.Item>
          </Show>

          <Show when={status() === "connected"}>
            <DropdownMenu.Item
              onSelect={() => console.log("Déconnexion à implémenter")}
              disabled={isTransitioning()}
              class="hover:bg-(--theme-hover) data-disabled:opacity-50 flex cursor-pointer items-center rounded-sm px-2 py-1.5 text-xs transition-colors outline-none"
            >
              <TbPlugX class="text-(--icons) mr-2 size-4" />
              <span>Disconnect</span>
            </DropdownMenu.Item>
          </Show>

          <Show when={status() === "connected" || url()}>
            <DropdownMenu.Item
              onSelect={() => refetch()}
              disabled={isTransitioning()}
              class="hover:bg-(--theme-hover) data-disabled:opacity-50 flex cursor-pointer items-center rounded-sm px-2 py-1.5 text-xs transition-colors outline-none"
            >
              <TbRefresh class="text-(--icons) mr-2 size-4" />
              <span>Reconnect</span>
            </DropdownMenu.Item>
          </Show>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu>
  );
};
