/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show } from "solid-js";
import { FiX } from "solid-icons/fi";
import { useTimeline } from "../context/TimelineContext";
import {
  EVENT_ACCENTS,
  PAD_L,
  RULER_H,
  type TimelineEvent,
  type LaidEvent,
} from "../types";
import { fmtTime } from "../utils";

export function TimelineClip(props: {
  ev: TimelineEvent;
  layout: LaidEvent | undefined;
  trackHeight: number;
}) {
  const { spacing, selectedId, setSelectedId, setContextMenu, deleteEvent } =
    useTimeline();

  const a = () => EVENT_ACCENTS[props.ev.type];
  const isDuring = () => props.ev.type === "during";
  const isPoint = () => !isDuring();
  const selected = () => selectedId() === props.ev.id;
  const layout = () => props.layout;

  const handlePointerDown = (e: PointerEvent) => {
    if (e.button !== 0 || !layout()) return;
    e.stopPropagation();
    setSelectedId(props.ev.id);
  };

  const handleContextMenu = (e: MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setSelectedId(props.ev.id);

    const container = document.querySelector("[data-timeline-container]");
    if (container) {
      const rect = container.getBoundingClientRect();
      let cx = e.clientX - rect.left;
      let cy = e.clientY - rect.top;

      if (cx + 170 > rect.width) cx = rect.width - 170;
      if (cy + 160 > rect.height) cy = rect.height - 160;

      setContextMenu({ type: "event", event: props.ev, x: cx, y: cy });
    }
  };

  const currentXPx = () => Math.max(PAD_L, layout()?.xPx || 0);
  const visualT1 = () => Math.max(0, layout()?.t1 || 0);
  const w = () => layout()?.wPx || 0;

  const baseBorderColor = () => (selected() ? a().mark : "var(--border)");
  const bTop = () =>
    isDuring() ? `3px solid ${a().mark}` : `1px solid ${baseBorderColor()}`;
  const bLeft = () =>
    !isDuring() ? `3px solid ${a().mark}` : `1px solid ${baseBorderColor()}`;

  const gridStepPx = () => {
    const pps = spacing();
    if (pps > 100) return pps;
    if (pps > 20) return pps * 5;
    return pps * 10;
  };

  const isMiniLevel = () => props.trackHeight < 40 || w() < 60;
  const isMediumLevel = () =>
    !isMiniLevel() && (props.trackHeight < 80 || w() < 120);
  const isMaxLevel = () => !isMiniLevel() && !isMediumLevel();

  return (
    <div
      onPointerDown={handlePointerDown}
      onContextMenu={handleContextMenu}
      class="group absolute overflow-hidden select-none flex flex-col cursor-pointer transition-shadow duration-100 isolate rounded-[3px] timeline-clip"
      classList={{
        hidden: !layout(),
        "z-[35]": selected(),
        "z-[30]": !selected(),
      }}
      style={{
        left: `${currentXPx()}px`,
        top: `${RULER_H + (layout()?.track || 0) * props.trackHeight + 2}px`,
        width: `${w()}px`,
        height: `${props.trackHeight - 4}px`,
        "border-top": bTop(),
        "border-left": bLeft(),
        "border-right": `1px solid ${baseBorderColor()}`,
        "border-bottom": `1px solid ${baseBorderColor()}`,
        "box-shadow": selected()
          ? `0 0 0 1px ${a().mark}, 0 0 12px ${a().mark}66`
          : "0 1px 3px rgba(0,0,0,0.05)",
      }}
    >
      <div class="absolute inset-0 pointer-events-none -z-20 bg-[var(--bg)]" />
      <div
        class="absolute inset-0 pointer-events-none -z-10"
        style={{
          background: selected() ? "var(--sidebar-active-bg)" : "var(--pre-bg)",
        }}
      />
      <div
        class="absolute inset-0 pointer-events-none z-0 opacity-15"
        style={{
          "background-image": `linear-gradient(to right, ${a().mark}33 1px, transparent 1px)`,
          "background-size": `${gridStepPx()}px 100%`,
          "background-position": "0 0",
        }}
      />

      <button
        class="absolute top-1 right-1 size-4 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-[var(--pre-bg)]/90 rounded-[2px] text-[var(--fg)] hover:bg-red-500 hover:text-white z-20 cursor-pointer"
        onPointerDown={(e) => {
          e.stopPropagation();
          deleteEvent(props.ev.id);
        }}
      >
        <FiX class="size-3" />
      </button>

      <div class="px-1.5 py-1 flex flex-col h-full relative z-10 overflow-hidden pointer-events-none justify-center">
        <Show when={isMiniLevel()}>
          <div class="flex items-center gap-1.5">
            <span
              class="font-bold tracking-tight uppercase shrink-0 text-[7px] px-1 rounded-[2px]"
              style={{ background: a().bg, color: a().text }}
            >
              {props.ev.type}
            </span>
            <span class="font-mono text-[8px] opacity-70 text-[var(--fg)] whitespace-nowrap">
              {isPoint() ? fmtTime(visualT1()) : `${fmtTime(visualT1())}→...`}
            </span>
          </div>
          <div class="font-sans text-[9px] truncate text-[var(--fg)] font-medium mt-[1px]">
            {props.ev.action}
          </div>
        </Show>

        <Show when={isMediumLevel()}>
          <div class="flex items-center gap-1.5 mb-0.5">
            <span
              class="font-bold tracking-tight uppercase shrink-0 text-[7px] px-1 rounded-[2px]"
              style={{ background: a().bg, color: a().text }}
            >
              {props.ev.type}
            </span>
            <span class="font-mono text-[8px] opacity-70 text-[var(--fg)] whitespace-nowrap">
              {isPoint()
                ? fmtTime(visualT1())
                : `${fmtTime(visualT1())}→${fmtTime(layout()?.t2 || 0)}`}
            </span>
          </div>
          <div class="font-sans text-[10px] leading-tight text-[var(--fg)] font-medium line-clamp-2">
            {props.ev.action}
          </div>
          <div class="text-[8px] font-mono opacity-50 mt-1 truncate text-[var(--fg)]">
            ID: {props.ev.id.substring(0, 8)}
          </div>
        </Show>

        <Show when={isMaxLevel()}>
          <div class="flex items-center gap-1.5 mb-1.5">
            <span
              class="font-bold tracking-tight uppercase shrink-0 text-[8px] px-1.5 py-0.5 rounded-[2px]"
              style={{ background: a().bg, color: a().text }}
            >
              {props.ev.type}
            </span>
            <span class="font-mono text-[9px] opacity-70 text-[var(--fg)] whitespace-nowrap">
              {isPoint()
                ? fmtTime(visualT1())
                : `${fmtTime(visualT1())} → ${fmtTime(layout()?.t2 || 0)}`}
            </span>
          </div>
          <div class="font-sans text-[11px] leading-snug text-[var(--fg)] font-medium line-clamp-3 mb-1.5">
            {props.ev.action}
          </div>
          <div class="flex flex-col gap-0.5 text-[9px] font-mono opacity-60 mt-auto text-[var(--fg)]">
            <span class="truncate">Source: {props.ev.source || "N/A"}</span>
            <span class="truncate">ID: {props.ev.id}</span>
          </div>
        </Show>
      </div>
    </div>
  );
}
