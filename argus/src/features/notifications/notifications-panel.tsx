/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { For, createSignal, createEffect } from "solid-js";
import { notifications } from "./store";

export function NotificationsPanel() {
  const [follow, setFollow] = createSignal(true);
  let containerRef!: HTMLDivElement;

  createEffect(() => {
    notifications();

    if (follow() && containerRef) {
      containerRef.scrollTop = containerRef.scrollHeight;
    }
  });

  return (
    <div class="flex flex-col gap-2 text-sm h-full">
      {/* Header with button */}
      <div class="flex items-center justify-between">
        <button
          onClick={() => setFollow((f) => !f)}
          class={`text-xs px-2 py-1 rounded border transition-colors ${
            follow()
              ? "bg-(--links) text-(--bg)"
              : "bg-transparent text-(--icons) border-border"
          }`}
        >
          {follow() ? "Follow ON" : "Follow OFF"}
        </button>
      </div>

      {/* scrollable notif list */}
      <div
        ref={containerRef}
        onScroll={(e) => {
          const el = e.currentTarget;

          const isAtBottom =
            el.scrollHeight - el.scrollTop - el.clientHeight < 10;

          if (!isAtBottom && follow()) {
            setFollow(false);
          }

          if (isAtBottom && !follow()) {
            setFollow(true);
          }
        }}
        class="flex flex-col gap-1 overflow-y-auto flex-1"
      >
        <For each={notifications()}>
          {(n) => {
            const time = new Date(n.date).toLocaleTimeString();

            return (
              <div class="flex items-center">
                <span class="text-muted-foreground pr-1">{time}</span>

                {n.type === "error" && (
                  <span class="text-red-500 pr-1">error</span>
                )}

                <span>- {n.message}</span>
              </div>
            );
          }}
        </For>
      </div>
    </div>
  );
}
