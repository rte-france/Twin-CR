/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createMemo,
  createEffect,
  onMount,
  onCleanup,
  Show,
  For,
  Index,
  untrack,
} from "solid-js";
import { FiChevronLeft, FiChevronRight } from "solid-icons/fi";
import { computeNLELayout, fmtTime } from "../utils";
import {
  PAD_L,
  RULER_H,
  TRACK_H,
  EVENT_ACCENTS,
  type LaidEvent,
} from "../types";
import { TimelineClip } from "./TimelineClip";
import { useTimeline } from "../context/TimelineContext";

/** Clips are only rendered within this distance (px) of the viewport (a replayed scenario can have ~30k events). */
const VIRTUAL_MARGIN_PX = 400;
/** The minimap shows event density per bin instead of one marker per event. */
const MINIMAP_BINS = 400;

const readScrollPos = (el: HTMLDivElement) => ({
  x: el.scrollLeft,
  w: el.clientWidth,
  y: el.scrollTop,
  h: el.clientHeight,
});

export function TimelineGrid() {
  const {
    events,
    currentTime,
    spacing,
    setSpacing,
    setSelectedId,
    setContextMenu,
  } = useTimeline();

  const [tlHeight, setTlHeight] = createSignal(300);
  const [trackHeight, setTrackHeight] = createSignal(TRACK_H);
  const [hoverPos, setHoverPos] = createSignal<{
    x: number;
    time: number;
  } | null>(null);

  const [scrollPos, setScrollPos] = createSignal({ x: 0, w: 1000, y: 0, h: 1000 });
  const [autoFollow, setAutoFollow] = createSignal(true);

  let scrollRef: HTMLDivElement | undefined;
  let timelineRef: HTMLDivElement | undefined;
  let isPanning = false;

  const layoutMap = createMemo(() => {
    const map = new Map<string, LaidEvent>();
    computeNLELayout(events(), spacing()).forEach((e) => map.set(e.id, e));
    return map;
  });

  const lodIntervals = createMemo(() => {
    const idealSecs = 80 / spacing();
    const intervals = [
      { major: 1, minor: 0.2 },
      { major: 5, minor: 1 },
      { major: 10, minor: 2 },
      { major: 30, minor: 5 },
      { major: 60, minor: 15 },
      { major: 300, minor: 60 },
    ];
    return (
      intervals.find((inv) => inv.major >= idealSecs) ||
      intervals[intervals.length - 1]
    );
  });

  const canvasDim = createMemo(() => {
    let maxTrack = 0,
      maxT = 0;
    layoutMap().forEach((val) => {
      if (val.track > maxTrack) maxTrack = val.track;
      if (val.t2 > maxT) maxT = val.t2;
    });
    return {
      w: PAD_L + (maxT + lodIntervals().major * 2) * spacing() + 200,
      h: Math.max(tlHeight(), RULER_H + (maxTrack + 1) * trackHeight()),
    };
  });

  const ticksList = createMemo(() => {
    const { major, minor } = lodIntervals();
    const pps = spacing();
    const s = scrollPos();

    const viewStartT = Math.max(0, (s.x - PAD_L - 300) / pps);
    const viewEndT = (s.x + s.w - PAD_L + 300) / pps;

    const maxT = Math.max(
      currentTime() + major * 2,
      (canvasDim().w - PAD_L) / pps,
    );

    const startT = Math.floor(viewStartT / minor) * minor;
    const endT = Math.min(maxT, Math.ceil(viewEndT / minor) * minor);

    const arr = [];
    for (let t = startT, index = 0; t <= endT; t += minor, index++) {
      arr.push({
        t,
        major:
          Math.abs(t % major) < 0.001 || Math.abs((t % major) - major) < 0.001,
        x: PAD_L + t * pps,
        index,
      });
    }
    return arr;
  });

  const blocksList = createMemo(() => {
    const { major } = lodIntervals();
    const pps = spacing();
    const s = scrollPos();

    const viewStartT = Math.max(0, (s.x - PAD_L - 300) / pps);
    const viewEndT = (s.x + s.w - PAD_L + 300) / pps;

    const maxT = Math.max(
      currentTime() + major * 2,
      (canvasDim().w - PAD_L) / pps,
    );

    const startT = Math.floor(viewStartT / major) * major;
    const endT = Math.min(maxT, Math.ceil(viewEndT / major) * major);

    const blocks = [];
    for (let currentT = startT; currentT <= endT; currentT += major) {
      if (Math.round(currentT / major) % 2 !== 0) {
        blocks.push({ x: PAD_L + currentT * pps, w: major * pps });
      }
    }
    return blocks;
  });

  const timeBounds = createMemo(() => {
    let maxT = Math.max(currentTime() + 60, 300);
    layoutMap().forEach((val) => {
      if (val.t2 > maxT) maxT = val.t2;
    });
    return maxT;
  });

  let scrollTimeout: ReturnType<typeof setTimeout>;

  const handleScroll = () => {
    if (scrollRef)
      setScrollPos(readScrollPos(scrollRef));

    clearTimeout(scrollTimeout);
    scrollTimeout = setTimeout(() => {
      if (scrollRef) {
        const timeAtLeft = scrollRef.scrollLeft / untrack(spacing);
        localStorage.setItem("timeline-scroll-time", String(timeAtLeft));
        localStorage.setItem("timeline-scroll-y", String(scrollRef.scrollTop));
      }
    }, 150);
  };

  createEffect(() => {
    const syncScroll = () => {
      if (scrollRef) {
        setScrollPos(readScrollPos(scrollRef));
      }
    };

    if (scrollRef) {
      scrollRef.addEventListener("scroll", syncScroll);
      window.addEventListener("resize", syncScroll);
      setTimeout(syncScroll, 150);
    }

    onCleanup(() => {
      if (scrollRef) scrollRef.removeEventListener("scroll", syncScroll);
      window.removeEventListener("resize", syncScroll);
    });
  });

  // Only the clips intersecting the viewport (+ margin) are rendered. Events keep their object between polls,
  // so a clip is only created/removed when it enters/leaves the viewport.
  const visibleEvents = createMemo(() => {
    const s = scrollPos();
    const th = trackHeight();
    const layout = layoutMap();
    const x0 = s.x - VIRTUAL_MARGIN_PX;
    const x1 = s.x + s.w + VIRTUAL_MARGIN_PX;
    const trackMin = Math.floor((s.y - VIRTUAL_MARGIN_PX - RULER_H) / th);
    const trackMax = Math.ceil((s.y + s.h + VIRTUAL_MARGIN_PX - RULER_H) / th);
    return events().filter((ev) => {
      const l = layout.get(ev.id);
      return (
        l !== undefined &&
        l.xPx + l.wPx >= x0 &&
        l.xPx <= x1 &&
        l.track >= trackMin &&
        l.track <= trackMax
      );
    });
  });

  // Event types present in each minimap bin (a "during" event marks all the bins it spans)
  const minimapBins = createMemo(() => {
    const maxT = timeBounds();
    const marks = new Set<string>();
    layoutMap().forEach((l) => {
      const first = Math.min(MINIMAP_BINS - 1, Math.floor((l.t1 / maxT) * MINIMAP_BINS));
      const last =
        l.type === "during"
          ? Math.min(MINIMAP_BINS - 1, Math.floor((l.t2 / maxT) * MINIMAP_BINS))
          : first;
      for (let bin = first; bin <= last; bin++) marks.add(`${l.type}:${bin}`);
    });
    return [...marks].map((mark) => {
      const [type, bin] = mark.split(":");
      return { type: type as LaidEvent["type"], bin: Number(bin) };
    });
  });

  const viewWindow = createMemo(() => {
    const pps = spacing();
    const maxT = timeBounds();
    const s = scrollPos();

    const startT = Math.max(0, (s.x - PAD_L) / pps);
    const endT = Math.max(0, (s.x + s.w - PAD_L) / pps);

    const leftPct = Math.min(100, (startT / maxT) * 100);
    const widthPct = Math.min(100 - leftPct, ((endT - startT) / maxT) * 100);

    return { left: `${leftPct}%`, width: `${widthPct}%` };
  });

  onMount(() => {
    const storedTime = parseFloat(
      localStorage.getItem("timeline-scroll-time") || "0",
    );
    const storedY = parseFloat(
      localStorage.getItem("timeline-scroll-y") || "0",
    );

    setTimeout(() => {
      if (scrollRef) {
        scrollRef.scrollLeft = storedTime * untrack(spacing);
        scrollRef.scrollTop = isNaN(storedY) ? 0 : storedY;
        setScrollPos(readScrollPos(scrollRef));

        if (storedTime > 0) setAutoFollow(false);
      }
    }, 100);

    const ro = new ResizeObserver((entries) => {
      setTlHeight(entries[0].contentRect.height);
      if (scrollRef)
        setScrollPos(readScrollPos(scrollRef));
    });
    if (timelineRef) ro.observe(timelineRef);

    const handleWheel = (e: WheelEvent) => {
      if (!scrollRef) return;
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const mouseX =
          e.clientX -
          scrollRef.getBoundingClientRect().left +
          scrollRef.scrollLeft;
        const timeAtMouse = (mouseX - PAD_L) / spacing();
        const newPps = Math.max(
          1,
          Math.min(500, spacing() * Math.exp(-e.deltaY * 0.005)),
        );
        setSpacing(Math.round(newPps * 10) / 10);
        scrollRef.scrollLeft =
          PAD_L +
          timeAtMouse * newPps -
          (e.clientX - scrollRef.getBoundingClientRect().left);
      } else if (e.altKey) {
        e.preventDefault();
        setTrackHeight((th) =>
          Math.max(24, Math.min(200, th * Math.exp(-e.deltaY * 0.005))),
        );
      } else {
        e.preventDefault();
        if (e.shiftKey) {
          scrollRef.scrollTop += (e.deltaY || e.deltaX) * 0.5;
        } else {
          scrollRef.scrollLeft += (e.deltaX || e.deltaY) * 0.5;
        }
      }

      setAutoFollow(false);
      handleScroll();
    };

    if (scrollRef)
      scrollRef.addEventListener("wheel", handleWheel, { passive: false });
    onCleanup(() => {
      ro.disconnect();
      if (scrollRef) scrollRef.removeEventListener("wheel", handleWheel);
    });
  });

  createEffect(() => {
    const t = currentTime();
    if (scrollRef && autoFollow()) {
      const x = PAD_L + t * untrack(spacing);

      scrollRef.scrollLeft = Math.max(0, x - 100);
    }
  });

  const handlePointerMove = (e: PointerEvent) => {
    if (!scrollRef || isPanning) return;
    const rect = scrollRef.getBoundingClientRect();
    const mouseX = e.clientX - rect.left + scrollRef.scrollLeft;
    const time = Math.max(0, (mouseX - PAD_L) / spacing());
    setHoverPos({ x: mouseX, time });
  };

  const handlePan = (e: PointerEvent, isRuler = false) => {
    if (e.button !== 0 || !scrollRef) return;
    const target = e.target as HTMLElement;
    if (!isRuler && target.closest('[data-interactive="true"]')) return;

    if (isRuler) {
      e.stopPropagation();
      e.preventDefault();
    }

    let startX = e.clientX;
    let startY = e.clientY;
    let startScrollX = scrollRef.scrollLeft;
    let startScrollY = scrollRef.scrollTop;
    let startPps = spacing();
    let hasMoved = false;

    isPanning = true;
    scrollRef.style.cursor = isRuler ? "row-resize" : "grabbing";
    setHoverPos(null);

    const onMove = (moveEvent: PointerEvent) => {
      hasMoved = true;
      setAutoFollow(false);

      if (isRuler && scrollRef) {
        const newPps = Math.max(
          1,
          Math.min(
            500,
            startPps * Math.exp(-(moveEvent.clientY - startY) * 0.01),
          ),
        );
        untrack(() => setSpacing(Math.round(newPps * 10) / 10));
        scrollRef.scrollLeft =
          PAD_L +
          ((startX -
            scrollRef.getBoundingClientRect().left +
            startScrollX -
            PAD_L) /
            startPps) *
            newPps -
          (startX - scrollRef.getBoundingClientRect().left) -
          (moveEvent.clientX - startX);
      } else if (scrollRef) {
        scrollRef.scrollLeft = startScrollX - (moveEvent.clientX - startX);
        scrollRef.scrollTop = startScrollY - (moveEvent.clientY - startY);
      }
      setScrollPos(readScrollPos(scrollRef));
      handleScroll();
    };

    const onEnd = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onEnd);
      if (scrollRef) scrollRef.style.cursor = "crosshair";
      isPanning = false;
      if (!isRuler && !hasMoved) setSelectedId(null);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onEnd);
  };

  const handleDblClick = () => {
    if (!scrollRef) return;
    const targetX = PAD_L + currentTime() * spacing() - 100;
    scrollRef.scrollTo({ left: Math.max(0, targetX), behavior: "smooth" });

    setAutoFollow(true);
    handleScroll();
  };

  const handleBackgroundContextMenu = (e: MouseEvent) => {
    if ((e.target as HTMLElement).closest(".timeline-clip")) return;
    e.preventDefault();
    e.stopPropagation();
    if (!scrollRef) return;

    const container = document.querySelector("[data-timeline-container]");
    if (!container) return;

    const rect = container.getBoundingClientRect();
    let cx = e.clientX - rect.left;
    let cy = e.clientY - rect.top;

    if (cx + 170 > rect.width) cx = rect.width - 170;
    if (cy + 160 > rect.height) cy = rect.height - 160;

    const mouseX =
      e.clientX - scrollRef.getBoundingClientRect().left + scrollRef.scrollLeft;
    const time = Math.max(0, (mouseX - PAD_L) / spacing());

    setContextMenu({ type: "background", time, x: cx, y: cy });
  };

  const handleMinimapClick = (e: MouseEvent) => {
    if (!scrollRef) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const targetTime = percent * timeBounds();
    scrollRef.scrollLeft = Math.max(
      0,
      PAD_L + targetTime * untrack(spacing) - 100,
    );
    setAutoFollow(false);
    handleScroll();
  };

  const handleRecenter = () => {
    if (!scrollRef) return;
    const targetX = PAD_L + currentTime() * untrack(spacing) - 100;
    scrollRef.scrollLeft = Math.max(0, targetX);
    setAutoFollow(true);
    handleScroll();
  };

  const handleWindowDrag = (e: PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
    if (!scrollRef) return;

    const target = e.currentTarget as HTMLElement;
    const parent = target.parentElement;
    if (!parent) return;

    const parentRect = parent.getBoundingClientRect();
    const pps = spacing();
    const maxT = timeBounds();

    const onPointerMove = (moveEvent: PointerEvent) => {
      const currentMouseXOnMinimap = moveEvent.clientX - parentRect.left;
      const percent = Math.max(
        0,
        Math.min(1, currentMouseXOnMinimap / parentRect.width),
      );
      const targetCenterTime = percent * maxT;
      if (scrollRef) {
        scrollRef.scrollLeft = Math.max(
          0,
          PAD_L + targetCenterTime * pps - 100,
        );
      }
    };

    const onPointerUp = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  };

  return (
    <div
      ref={timelineRef}
      class="flex-1 flex flex-col overflow-hidden relative min-h-[200px] bg-[var(--bg)] border-t border-[var(--border)]"
    >
      <div class="h-6 bg-[var(--sidebar-bg)] border-b border-[var(--divider)] flex items-center shrink-0 relative overflow-hidden group z-50">
        <button
          type="button"
          onClick={handleRecenter}
          class="absolute left-0 top-0 bottom-0 px-2 bg-gradient-to-r from-[var(--sidebar-bg)] via-[var(--sidebar-bg)] to-transparent z-20 text-[var(--icons)] hover:text-[var(--links)] opacity-0 group-hover:opacity-100 transition-opacity"
          title="Recenter to Playhead"
        >
          <FiChevronLeft class="size-4" />
        </button>

        <div
          class="flex-1 h-full relative cursor-crosshair"
          onPointerDown={handleMinimapClick}
        >
          <div
            class="absolute top-0 bottom-0 bg-[var(--links)]/10 border-x border-[var(--links)]/30 z-30 cursor-ew-resize transition-[opacity,background-color] duration-75"
            style={viewWindow()}
            onPointerDown={handleWindowDrag}
          />

          <div
            class="absolute top-0 bottom-0 left-0 bg-[var(--icons)]/5 z-0 pointer-events-none transition-all duration-100"
            style={{ width: `${(currentTime() / timeBounds()) * 100}%` }}
          />

          <Show when={hoverPos()}>
            <div
              class="absolute top-0 bottom-0 w-[1px] bg-[var(--icons)] opacity-25 z-20 pointer-events-none border-l border-solid border-[var(--icons)]"
              style={{ left: `${(hoverPos()!.time / timeBounds()) * 100}%` }}
            />
          </Show>

          <div
            class="absolute top-0 bottom-0 w-[1px] bg-[var(--links)] z-20 pointer-events-none shadow-[0_0_4px_var(--links)] transition-all duration-100"
            style={{ left: `${(currentTime() / timeBounds()) * 100}%` }}
          >
            <div class="absolute top-0 w-1.5 h-2 rounded-br-[2px] bg-[var(--links)]" />
          </div>

          <Index each={minimapBins()}>
            {(mark) => (
              <div
                class="absolute top-1/2 -translate-y-1/2 h-2 rounded-[1px] z-10 pointer-events-none transition-opacity duration-200"
                style={{
                  left: `${(mark().bin / MINIMAP_BINS) * 100}%`,
                  width: `${100 / MINIMAP_BINS}%`,
                  background: EVENT_ACCENTS[mark().type].mark,
                  opacity: (mark().bin / MINIMAP_BINS) * timeBounds() < currentTime() ? 0.3 : 0.8,
                  "min-width": "2px",
                }}
              />
            )}
          </Index>
        </div>

        <button
          type="button"
          onClick={handleRecenter}
          class="absolute right-0 top-0 bottom-0 px-2 bg-gradient-to-l from-[var(--sidebar-bg)] via-[var(--sidebar-bg)] to-transparent z-20 text-[var(--icons)] hover:text-[var(--links)] opacity-0 group-hover:opacity-100 transition-opacity"
          title="Recenter to Playhead"
        >
          <FiChevronRight class="size-4" />
        </button>
      </div>

      <div
        ref={scrollRef}
        onPointerDown={(e) => handlePan(e)}
        onPointerMove={handlePointerMove}
        onPointerLeave={() => setHoverPos(null)}
        onScroll={handleScroll}
        onDblClick={handleDblClick}
        onContextMenu={handleBackgroundContextMenu}
        class="overflow-auto flex-1 select-none cursor-crosshair scrollbar-thin timeline-grid-scroll-view"
        style={{ "scrollbar-color": "var(--scrollbar) transparent" }}
      >
        <div
          class="relative"
          style={{
            width: `${Math.max(scrollRef?.clientWidth || 0, canvasDim().w)}px`,
            height: `${canvasDim().h}px`,
          }}
        >
          <div class="absolute inset-0 pointer-events-none z-0">
            <div
              class="absolute inset-x-0"
              style={{ top: `${RULER_H}px`, bottom: 0 }}
            >
              <For each={blocksList()}>
                {(block) => (
                  <div
                    class="absolute inset-y-0 bg-[var(--table-alternate-bg)]"
                    style={{ left: `${block.x}px`, width: `${block.w}px` }}
                  />
                )}
              </For>
            </div>

            <div
              class="absolute inset-x-0 bottom-0"
              style={{
                top: `${RULER_H}px`,
                "background-image": `linear-gradient(to bottom, transparent, transparent ${trackHeight() - 1}px, var(--divider) ${trackHeight() - 1}px, var(--divider) ${trackHeight()}px)`,
                "background-size": `100% ${trackHeight()}px`,
              }}
            />

            <div
              class="absolute inset-x-0 bottom-0"
              style={{ top: `${RULER_H}px` }}
            >
              <For each={ticksList()}>
                {(tick) => (
                  <Show when={tick.major}>
                    <div
                      class="absolute inset-y-0 w-[1px] bg-[var(--divider)] pointer-events-none"
                      style={{ left: `${tick.x}px` }}
                    />
                  </Show>
                )}
              </For>
            </div>
          </div>

          <Show when={hoverPos()}>
            <div
              class="absolute inset-y-0 pointer-events-none z-[45]"
              style={{ left: `${hoverPos()!.x}px` }}
            >
              <div class="absolute inset-y-0 left-0 w-[1px] border-l border-solid border-[var(--icons)] opacity-25" />
            </div>
          </Show>

          <div
            class="absolute inset-y-0 pointer-events-none z-[45]"
            style={{ left: `${PAD_L + currentTime() * spacing()}px` }}
          >
            <div class="absolute inset-y-0 left-0 w-[1px] bg-[var(--links)] shadow-[0_0_4px_var(--links)]" />
          </div>

          <div
            class="sticky top-0 z-[50] cursor-row-resize bg-[var(--sidebar-bg)] border-b border-[var(--divider)]"
            onPointerDown={(e) => handlePan(e, true)}
            data-interactive="true"
            style={{ height: `${RULER_H}px` }}
          >
            <For each={ticksList()}>
              {(tick) => (
                <div>
                  <div
                    class="absolute w-[1px] z-[2] bg-[var(--icons)] pointer-events-none"
                    style={{
                      left: `${tick.x}px`,
                      top: `${tick.major ? 16 : 24}px`,
                      height: `${tick.major ? 16 : 8}px`,
                    }}
                  />
                  <Show when={tick.major}>
                    <div
                      class="absolute top-[2px] text-[9px] font-mono whitespace-nowrap z-[2] text-[var(--fg)] opacity-70 pointer-events-none ml-1"
                      style={{ left: `${tick.x}px` }}
                    >
                      {fmtTime(tick.t)}
                    </div>
                  </Show>
                </div>
              )}
            </For>

            <Show when={hoverPos()}>
              <div
                class="absolute top-[2px] font-mono text-[9px] font-medium text-[var(--icons)] pointer-events-none z-[51] ml-1.5"
                style={{ left: `${hoverPos()!.x}px` }}
              >
                {fmtTime(hoverPos()!.time)}
              </div>
            </Show>

            <div
              class="absolute top-0 w-2 h-3.5 rounded-br-[3px] bg-[var(--links)] pointer-events-none z-[51]"
              style={{ left: `${PAD_L + currentTime() * spacing()}px` }}
            />
          </div>

          <For each={visibleEvents()}>
            {(ev) => (
              <TimelineClip
                ev={ev}
                layout={layoutMap().get(ev.id)}
                trackHeight={trackHeight()}
              />
            )}
          </For>
        </div>
      </div>
    </div>
  );
}
