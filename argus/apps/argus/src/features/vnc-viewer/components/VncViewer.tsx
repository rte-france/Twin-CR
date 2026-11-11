/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, onCleanup, Show, type Component } from "solid-js";

interface VncViewerProps {
  url: string;
}

const VNC_PARAMS = "autoconnect=true&resize=remote&reconnect=true&reconnect_delay=2000&quality=6&compression=2&view_only=false";
const POLL_INTERVAL = 3000;

export const VncViewer: Component<VncViewerProps> = (props) => {
  const [interactive, setInteractive] = createSignal(false);
  const [reachable, setReachable] = createSignal(false);
  let iframeRef: HTMLIFrameElement | undefined;
  let overlayRef: HTMLDivElement | undefined;
  let pollTimer: ReturnType<typeof setInterval> | undefined;

  const check = async () => {
    try {
      await fetch(props.url, { mode: "no-cors" });
      setReachable(true);
      clearInterval(pollTimer);
    } catch {
      setReachable(false);
    }
  };

  createEffect(() => {
    if (!props.url) return;
    clearInterval(pollTimer);
    setReachable(false);
    setInteractive(false);
    check();
    pollTimer = setInterval(check, POLL_INTERVAL);
    onCleanup(() => clearInterval(pollTimer));
  });

  const enterInteractive = () => {
    setInteractive(true);
    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        iframeRef && !iframeRef.contains(target) &&
        overlayRef && !overlayRef.contains(target)
      ) {
        setInteractive(false);
        window.removeEventListener("mousedown", onMouseDown);
      }
    };
    window.addEventListener("mousedown", onMouseDown);
  };

  const src = () => {
    if (!reachable()) return null;
    const sep = props.url.includes("?") ? "&" : "?";
    return `${props.url}${sep}${VNC_PARAMS}`;
  };

  return (
    <div class="relative w-full h-full">
      <Show when={src()}>
        {(s) => (
          <iframe
            ref={iframeRef}
            src={s()}
            class="w-full h-full border-none"
          />
        )}
      </Show>
      <Show when={!reachable()}>
        <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-bg text-fg">
          <div class="size-6 rounded-full border-2 border-border border-t-links animate-spin" />
          <span class="text-sm opacity-50">Connecting to {props.url}…</span>
        </div>
      </Show>
      {/* Add cover when clicking out of the window to stop capturing the cursor and allow resizing the window */}
      <Show when={!interactive()}>
        <div ref={overlayRef} class="absolute inset-0" onMouseDown={enterInteractive} />
      </Show>
    </div>
  );
};
