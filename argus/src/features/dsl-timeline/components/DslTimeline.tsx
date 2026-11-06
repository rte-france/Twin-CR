/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show } from "solid-js";
import { FiServer, FiAlertCircle, FiX } from "solid-icons/fi";
import { TimelineProvider, useTimeline } from "../context/TimelineContext";
import { TimelineHeader } from "./TimelineHeader";
import { TimelineGrid } from "./TimelineGrid";
import { TimelineContextMenu } from "./TimelineContextMenu";
import { ClipInspector } from "./ClipInspector";
import { WhenEventsDrawer } from "./WhenEventsDrawer";

function DslTimelineInner() {
  const { statusError, mutationError, dismissMutationError } = useTimeline();

  return (
    <div
      data-timeline-container
      class="flex flex-col w-full h-full bg-(--bg) text-(--fg) font-sans relative overflow-hidden isolate"
    >
      <TimelineHeader />

      <Show when={mutationError()}>
        <div class="flex items-center gap-1.5 px-3 py-1.5 border-b border-(--warning-border) bg-(--warning-bg) text-(--warning-icon) text-[10px] shrink-0">
          <FiAlertCircle class="size-3 shrink-0" />
          <span class="flex-1 break-all font-mono">{mutationError()}</span>
          <button
            type="button"
            onClick={dismissMutationError}
            class="shrink-0 p-0.5 rounded-[2px] hover:bg-(--warning-icon)/10 cursor-pointer"
            title="Dismiss"
          >
            <FiX class="size-3" />
          </button>
        </div>
      </Show>

      <div class="flex-1 flex overflow-hidden w-full relative">
        <WhenEventsDrawer />

        <main class="flex-1 flex flex-col overflow-hidden relative z-10 h-full">
          <Show when={statusError()}>
            <div class="m-2 p-1.5 border border-(--warning-border) bg-(--warning-bg) text-(--warning-icon) text-[10px] rounded-sm flex items-center gap-1.5 shadow-sm">
              <FiServer class="size-3" /> Connection Error
            </div>
          </Show>
          <Show when={!statusError()}>
            <TimelineGrid />
          </Show>
        </main>
      </div>

      <ClipInspector />

      <TimelineContextMenu />
    </div>
  );
}

export function DslTimeline() {
  return (
    <TimelineProvider>
      <DslTimelineInner />
    </TimelineProvider>
  );
}
