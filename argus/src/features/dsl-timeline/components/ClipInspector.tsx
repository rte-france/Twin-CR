/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, createSignal, createEffect, on } from "solid-js";
import {
  FiX,
  FiClock,
  FiTerminal,
  FiHash,
  FiDatabase,
  FiCopy,
  FiCheck,
  FiEdit2,
  FiAlertCircle,
} from "solid-icons/fi";
import { FaSolidSpinner } from "solid-icons/fa";
import { useTimeline } from "../context/TimelineContext";
import { EVENT_ACCENTS } from "../types";
import { fmtTime } from "../utils";

export function ClipInspector() {
  const { selectedId, setSelectedId, events, editEvent } = useTimeline();

  const [drawerHeight, setDrawerHeight] = createSignal(
    Number(localStorage.getItem("timeline-drawer-h")) || 220,
  );
  createEffect(() =>
    localStorage.setItem("timeline-drawer-h", String(drawerHeight())),
  );

  const [copiedId, setCopiedId] = createSignal(false);
  const [copiedDsl, setCopiedDsl] = createSignal(false);

  const [isEditing, setIsEditing] = createSignal(false);
  const [editText, setEditText] = createSignal("");
  const [isSaving, setIsSaving] = createSignal(false);
  const [editError, setEditError] = createSignal<string | null>(null);

  const event = () => events().find((e) => e.id === selectedId());
  const a = () => (event() ? EVENT_ACCENTS[event()!.type] : null);
  const isReady = () => event()?.status === "ready";

  // Leaving edit mode whenever the selection changes (including the id swap after a successful save).
  createEffect(
    on(selectedId, () => {
      setIsEditing(false);
      setEditError(null);
    }),
  );

  const startEditing = () => {
    if (!event()) return;
    setEditText(event()!.action);
    setEditError(null);
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setEditError(null);
  };

  const saveEditing = () => {
    const ev = event();
    if (!ev || isSaving()) return;

    setIsSaving(true);
    editEvent(ev.id, editText())
      .then((newId) => {
        setIsSaving(false);
        setIsEditing(false);
        setSelectedId(newId);
      })
      .catch((err: Error) => {
        setIsSaving(false);
        setEditError(err.message);
      });
  };

  const formatDuration = (ev: NonNullable<ReturnType<typeof event>>) => {
    if (ev.type === "during" && ev.from !== undefined && ev.to !== undefined) {
      return `${Number(ev.to) - Number(ev.from)}s`;
    }
    return "Instant";
  };

  const handleCopyId = () => {
    if (!event()) return;
    navigator.clipboard.writeText(event()!.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleCopyDsl = () => {
    if (!event()) return;
    navigator.clipboard.writeText(event()!.action);
    setCopiedDsl(true);
    setTimeout(() => setCopiedDsl(false), 2000);
  };

  const handleResizeStart = (e: PointerEvent) => {
    e.preventDefault();
    const startY = e.clientY;
    const startH = drawerHeight();

    const onMove = (m: PointerEvent) =>
      setDrawerHeight(
        Math.max(100, Math.min(800, startH + (startY - m.clientY))),
      );
    const onEnd = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onEnd);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onEnd);
  };

  return (
    <div
      class="w-full bg-(--sidebar-bg) border-t border-(--border) transition-opacity duration-300 ease-in-out flex flex-col z-30 shrink-0"
      style={{
        height: event() ? `${drawerHeight()}px` : "0px",
        opacity: event() ? "1" : "0",
        "pointer-events": event() ? "auto" : "none",
      }}
    >
      <Show when={event() && a()}>
        <div
          class="h-1 w-full cursor-row-resize hover:opacity-80 transition-opacity"
          onPointerDown={handleResizeStart}
        />

        <header class="flex items-center justify-between px-4 py-2 border-b border-(--border-light) bg-(--bg)/50">
          <div class="flex items-center gap-3">
            <span
              class="px-2 py-0.5 rounded-xs text-[9px] font-bold tracking-widest uppercase shadow-sm"
              style={{
                background: a()!.bg,
                color: a()!.text,
                border: `1px solid ${a()!.mark}`,
              }}
            >
              {event()!.type}
            </span>
            <div class="flex items-center gap-1.5 group">
              <span class="font-mono text-[11px] text-(--fg) opacity-80 flex items-center gap-1">
                <FiHash class="size-3" /> {event()!.id}
              </span>
              <button
                type="button"
                onClick={handleCopyId}
                class="p-1 rounded-xs text-(--icons) hover:bg-(--theme-hover) hover:text-(--fg) transition-colors opacity-0 group-hover:opacity-100"
                title="Copy ID"
              >
                <Show when={copiedId()} fallback={<FiCopy class="size-3" />}>
                  <FiCheck class="size-3 text-(--success-color)" />
                </Show>
              </button>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSelectedId(null)}
            class="p-1 rounded-sm text-(--icons) hover:bg-(--warning-bg) hover:text-(--warning-icon) transition-colors"
          >
            <FiX class="size-4" />
          </button>
        </header>

        <div class="flex-1 flex overflow-hidden">
          <div class="w-1/3 min-w-62.5 p-4 flex flex-col gap-4 border-r border-(--border-light) overflow-y-auto scrollbar-thin">
            <div class="flex flex-col gap-1">
              <span class="text-[8px] uppercase tracking-wider font-bold text-(--icons) flex items-center gap-1">
                <FiClock class="size-2.5" /> Timing
              </span>
              <div class="grid grid-cols-2 gap-2 mt-1">
                <div class="bg-(--pre-bg) border border-(--border-light) rounded-[3px] p-2 flex flex-col">
                  <span class="text-[8px] text-(--icons) uppercase">Start</span>
                  <span class="font-mono text-[11px] font-medium text-(--fg)">
                    {event()!.type === "during"
                      ? fmtTime(Number(event()!.from))
                      : fmtTime(Number(event()!.trigger))}
                  </span>
                </div>
                <div class="bg-(--pre-bg) border border-(--border-light) rounded-[3px] p-2 flex flex-col">
                  <span class="text-[8px] text-(--icons) uppercase">
                    Duration / End
                  </span>
                  <span class="font-mono text-[11px] font-medium text-(--fg)">
                    {formatDuration(event()!)}
                  </span>
                </div>
              </div>
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-[8px] uppercase tracking-wider font-bold text-(--icons) flex items-center gap-1">
                <FiDatabase class="size-2.5" /> Metadata
              </span>
              <div class="flex flex-col gap-1 mt-1">
                <div class="flex items-center justify-between text-[10px]">
                  <span class="text-(--icons)">Source:</span>
                  <span class="font-mono text-(--fg) bg-(--pre-bg) px-1 py-0.5 rounded-xs border border-(--border-light)">
                    {event()!.source || "System"}
                  </span>
                </div>
                <div class="flex items-center justify-between text-[10px]">
                  <span class="text-(--icons)">Status:</span>
                  <span class="font-sans font-bold text-(--links)">
                    {event()!.status || "READY"}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div class="flex-1 p-4 flex flex-col overflow-hidden bg-(--bg)/30">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[8px] uppercase tracking-wider font-bold text-(--icons) flex items-center gap-1">
                <FiTerminal class="size-2.5" /> DSL Command
              </span>
              <div class="flex items-center gap-1.5">
                <Show when={isEditing()}>
                  <button
                    type="button"
                    onClick={cancelEditing}
                    disabled={isSaving()}
                    class="px-2 py-0.5 rounded-xs border border-(--border-light) bg-(--pre-bg) text-[9px] text-(--fg) hover:bg-(--theme-hover) transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={saveEditing}
                    disabled={isSaving()}
                    class="flex items-center gap-1.5 px-2 py-0.5 rounded-xs border border-(--border-light) bg-(--pre-bg) text-[9px] text-(--success-color) hover:bg-(--theme-hover) transition-colors disabled:opacity-50"
                  >
                    <Show
                      when={!isSaving()}
                      fallback={<FaSolidSpinner class="size-2.5 animate-spin" />}
                    >
                      <FiCheck class="size-2.5" />
                    </Show>
                    Save
                  </button>
                </Show>
                <Show when={!isEditing() && isReady()}>
                  <button
                    type="button"
                    onClick={startEditing}
                    class="flex items-center gap-1.5 px-2 py-0.5 rounded-xs border border-(--border-light) bg-(--pre-bg) text-[9px] text-(--fg) hover:bg-(--theme-hover) transition-colors"
                    title="Edit (Ready events only)"
                  >
                    <FiEdit2 class="size-2.5" /> Edit
                  </button>
                </Show>
                <Show when={!isEditing()}>
                  <button
                    type="button"
                    onClick={handleCopyDsl}
                    class="flex items-center gap-1.5 px-2 py-0.5 rounded-xs border border-(--border-light) bg-(--pre-bg) text-[9px] text-(--fg) hover:bg-(--theme-hover) transition-colors"
                  >
                    <Show
                      when={copiedDsl()}
                      fallback={
                        <>
                          <FiCopy class="size-2.5" /> Copy
                        </>
                      }
                    >
                      <FiCheck class="size-2.5 text-(--success-color)" /> Copied!
                    </Show>
                  </button>
                </Show>
              </div>
            </div>

            <Show when={editError()}>
              <div class="flex items-center gap-1.5 mb-2 px-2 py-1 rounded-xs border border-(--warning-border) bg-(--warning-bg) text-(--warning-icon) text-[10px]">
                <FiAlertCircle class="size-3 shrink-0" />
                <span class="break-all">{editError()}</span>
              </div>
            </Show>

            <Show
              when={isEditing()}
              fallback={
                <div class="flex-1 bg-(--pre-bg) border border-(--border) rounded-[3px] shadow-inner p-3 overflow-y-auto scrollbar-thin">
                  <pre class="font-mono text-[11px] text-(--code-text) whitespace-pre-wrap wrap-break-word leading-relaxed">
                    {event()!.action}
                  </pre>
                </div>
              }
            >
              <textarea
                value={editText()}
                onInput={(e) => setEditText(e.currentTarget.value)}
                disabled={isSaving()}
                class="flex-1 bg-(--pre-bg) border border-(--links) rounded-[3px] shadow-inner p-3 font-mono text-[11px] text-(--code-text) whitespace-pre-wrap outline-none resize-none disabled:opacity-70"
              />
            </Show>
          </div>
        </div>
      </Show>
    </div>
  );
}
