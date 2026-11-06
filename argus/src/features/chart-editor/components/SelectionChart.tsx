/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  onMount,
  onCleanup,
  createEffect,
  on,
  createSignal,
  For,
  Show,
  type Component,
} from "solid-js";
import uPlot, { type Options, type AlignedData } from "uplot";
import "uplot/dist/uPlot.min.css";
import { FiList, FiChevronRight } from "solid-icons/fi";
import { ChartDataRow } from "@/services/chart";
import { GmSseData } from "@/services/game-master";

export function debounce<T extends (...args: any[]) => void>(fn: T, ms = 400) {
  let timeoutId: ReturnType<typeof setTimeout>;
  return function (this: any, ...args: Parameters<T>) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), ms);
  };
}

export interface SelectionChartProps {
  selectedData: ChartDataRow[];
  latestBatch: GmSseData[];
  currentTime: number;
  historicalData?: GmSseData[];
  onTimeRangeChange?: (min: number, max: number) => void;
  onResetZoom?: () => void;
}

const COLORS = [
  "#3b82f6",
  "#ef4444",
  "#10b981",
  "#f59e0b",
  "#8b5cf6",
  "#ec4899",
  "#06b6d4",
  "#f97316",
];

const WINDOW_TIME = 200;

const getUniqueKey = (item: any) => {
  const eqId = item.equipmentId || "";
  const type = item.isEstim ? "estim" : "tmts";
  return item.id
    ? `${item.id}-${type}`
    : `${eqId}-${item.kind}-${item.side || ""}-${type}`;
};

export const SelectionChart: Component<SelectionChartProps> = (props) => {
  let chartRef!: HTMLDivElement;
  let chartInstance: uPlot | undefined;

  let chartData: (number | null)[][] = [];
  let idToSeriesIndex = new Map<string, number>();

  let isUserZoomed = false;

  const [themeTrigger, setThemeTrigger] = createSignal(0);
  const [hoverIdx, setHoverIdx] = createSignal<number | null>(null);
  const [dataTick, setDataTick] = createSignal(0);
  const [hiddenSeries, setHiddenSeries] = createSignal<Set<number>>(new Set());
  const [showLegend, setShowLegend] = createSignal(true);

  const notifyTimeRange = debounce((min: number, max: number) => {
    if (props.onTimeRangeChange) {
      props.onTimeRangeChange(min, max);
    }
  }, 400);

  const toggleSeries = (seriesIdx: number) => {
    if (!chartInstance) return;
    const current = new Set(hiddenSeries());
    if (current.has(seriesIdx)) {
      current.delete(seriesIdx);
      chartInstance.setSeries(seriesIdx, { show: true });
    } else {
      current.add(seriesIdx);
      chartInstance.setSeries(seriesIdx, { show: false });
    }
    setHiddenSeries(current);
  };

  createEffect(
    on(
      () =>
        props.selectedData.map((d) => getUniqueKey(d)).join(",") +
        themeTrigger(),
      (_) => {
        if (chartInstance) {
          chartInstance.destroy();
          chartInstance = undefined;
        }

        const selected = props.selectedData;
        if (selected.length === 0) return;

        const sCount = selected.length + 1;

        chartData = Array(sCount)
          .fill(null)
          .map(() => [] as (number | null)[]);
        idToSeriesIndex.clear();
        isUserZoomed = false;
        setHiddenSeries(new Set<number>());
        setHoverIdx(null);

        const series: uPlot.Series[] = [{ label: "Time" }];

        selected.forEach((item, idx) => {
          const seriesIdx = idx + 1;
          const uniqueKey = getUniqueKey(item);

          idToSeriesIndex.set(uniqueKey, seriesIdx);

          const displayLabel = item.equipmentId || item.id;
          const color = COLORS[idx % COLORS.length];

          series.push({
            label: displayLabel,
            stroke: color,
            width: item.isEstim ? 1.5 : 2,
            dash: item.isEstim ? [5, 5] : undefined,
            spanGaps: true,
            paths: uPlot.paths.stepped
              ? uPlot.paths.stepped({ align: 1 })
              : undefined,
          });
        });

        const computed = getComputedStyle(chartRef);
        const fg = computed.getPropertyValue("--fg").trim() || "#000";
        const borderLight =
          computed.getPropertyValue("--border-light").trim() || "#ccc";
        const font = computed.getPropertyValue("--font").trim() || "sans-serif";
        const axisFont = `10px ${font}`;

        const axisConfig = {
          stroke: fg,
          font: axisFont,
          size: 50,
          grid: { stroke: borderLight, width: 1 },
          ticks: { stroke: borderLight, width: 1 },
        };

        let onMouseMove: (e: MouseEvent) => void;
        let onMouseUp: () => void;

        const opts: Options = {
          width: chartRef.clientWidth || 600,
          height: chartRef.clientHeight || 200,
          padding: [10, 60, 0, 10],
          legend: { show: false },
          scales: {
            x: { time: false, auto: false },
          },
          axes: [axisConfig, axisConfig],
          series,
          cursor: {
            drag: { x: true, y: false },
            sync: { key: "sync-charts", setSeries: true },
            dataIdx: (u, seriesIdx, closestIdx, xValue) => {
              const xData = u.data[0];
              if (!xData) return closestIdx;

              let idx = closestIdx;
              while (idx > 0 && xData[idx] > xValue) {
                idx--;
              }
              return idx;
            },
          },
          hooks: {
            setSelect: [
              () => {
                isUserZoomed = true;
              },
            ],
            setScale: [
              (u, key) => {
                if (key === "x" && isUserZoomed) {
                  const min = u.scales.x.min;
                  const max = u.scales.x.max;
                  if (min != null && max != null) {
                    notifyTimeRange(min, max);
                  }
                }
              },
            ],
            ready: [
              (u) => {
                let panning = false;
                let dragStartX = 0;
                let minX = 0;
                let maxX = 0;

                const onMouseDown = (e: MouseEvent) => {
                  if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
                    e.preventDefault();
                    panning = true;
                    dragStartX = e.clientX;
                    minX = u.scales.x.min ?? 0;
                    maxX = u.scales.x.max ?? 0;
                    u.over.style.cursor = "grabbing";
                  }
                };

                onMouseMove = (e: MouseEvent) => {
                  if (!panning) return;
                  isUserZoomed = true;

                  const dx = e.clientX - dragStartX;
                  const xRange = maxX - minX;
                  const dxVal = (dx / u.bbox.width) * xRange;

                  u.setScale("x", {
                    min: minX - dxVal,
                    max: maxX - dxVal,
                  });
                };

                onMouseUp = () => {
                  if (panning) {
                    panning = false;
                    u.over.style.cursor = "crosshair";
                  }
                };

                u.over.style.cursor = "crosshair";
                u.over.addEventListener("mousedown", onMouseDown);
                document.addEventListener("mousemove", onMouseMove);
                document.addEventListener("mouseup", onMouseUp);

                u.over.addEventListener("wheel", (e) => {
                  e.preventDefault();
                  isUserZoomed = true;

                  const { width } = u.bbox;
                  const { min, max } = u.scales.x;
                  const xRange = max! - min!;
                  const zoomFactor = e.deltaY < 0 ? 0.8 : 1.2;

                  const rect = u.over.getBoundingClientRect();
                  const mouseX = e.clientX - rect.left;
                  const ratio = mouseX / width;

                  const valAtMouse = min! + xRange * ratio;
                  const newRange = xRange * zoomFactor;

                  u.setScale("x", {
                    min: valAtMouse - newRange * ratio,
                    max: valAtMouse + newRange * (1 - ratio),
                  });
                });

                u.root.addEventListener("dblclick", () => {
                  isUserZoomed = false;
                  if (props.onResetZoom) {
                    props.onResetZoom();
                  }
                });
              },
            ],
            destroy: [
              () => {
                document.removeEventListener("mousemove", onMouseMove);
                document.removeEventListener("mouseup", onMouseUp);
              },
            ],
            setCursor: [
              (u) => {
                // 2. Synchronise l'index de la légende (hoverIdx) avec le point du passé
                const left = u.cursor.left;

                if (left === undefined || left < 0) {
                  setHoverIdx(null);
                  return;
                }

                const xVal = u.posToVal(left, "x");
                const xData = u.data[0];
                let idx = u.cursor.idx ?? 0;

                if (xData) {
                  while (idx > 0 && xData[idx] > xVal) {
                    idx--;
                  }
                }

                setHoverIdx(idx);
              },
            ],
            draw: [
              (u) => {
                const { ctx } = u;
                ctx.save();
                ctx.font = `bold 10px ${font}`;
                ctx.textAlign = "left";
                ctx.textBaseline = "middle";

                for (let i = 1; i < u.series.length; i++) {
                  const s = u.series[i];
                  if (!s.show) continue;

                  const dataX = u.data[0];
                  const dataY = u.data[i];

                  if (!dataX || !dataY) continue;

                  let i0 = u.valToIdx(u.scales.x.min ?? dataX[0]);
                  let i1 = u.valToIdx(
                    u.scales.x.max ?? dataX[dataX.length - 1],
                  );

                  let lastVal = null;
                  let lastX = null;

                  for (let j = i1; j >= i0; j--) {
                    if (dataY[j] != null) {
                      lastVal = dataY[j];
                      lastX = dataX[j];
                      break;
                    }
                  }

                  if (lastVal != null && lastX != null) {
                    const cx = u.valToPos(lastX, "x", true);
                    const cy = u.valToPos(lastVal, "y", true);

                    ctx.fillStyle = s.stroke as string;
                    ctx.fillText(
                      typeof s.label === "string" ? s.label : "",
                      cx + 6,
                      cy,
                    );
                  }
                }
                ctx.restore();
              },
            ],
          },
        };

        chartInstance = new uPlot(opts, chartData as AlignedData, chartRef);
      },
    ),
  );

  onMount(() => {
    const themeObserver = new MutationObserver(() => {
      requestAnimationFrame(() => setThemeTrigger((t) => t + 1));
    });

    [document.documentElement, document.body].forEach((el) => {
      themeObserver.observe(el, {
        attributes: true,
        attributeFilter: ["class", "data-theme", "style"],
      });
    });

    const ro = new ResizeObserver((entries) => {
      requestAnimationFrame(() => {
        for (const entry of entries) {
          if (chartInstance) {
            chartInstance.setSize({
              width: entry.contentRect.width,
              height: entry.contentRect.height,
            });
          }
        }
      });
    });

    ro.observe(chartRef);

    onCleanup(() => {
      themeObserver.disconnect();
      ro.disconnect();
    });
  });

  createEffect(
    on(
      () => props.historicalData,
      (history) => {
        if (
          !history ||
          history.length === 0 ||
          !chartInstance ||
          props.selectedData.length === 0
        )
          return;

        const sCount = props.selectedData.length + 1;

        const newChartData: (number | null)[][] = Array(sCount)
          .fill(null)
          .map(() => []);

        const eventsByTime = new Map<number, Map<number, number>>();

        history.forEach((event) => {
          const seriesIdx = idToSeriesIndex.get(event.id);
          if (seriesIdx === undefined) return;

          if (!eventsByTime.has(event.time)) {
            eventsByTime.set(event.time, new Map());
          }
          eventsByTime.get(event.time)!.set(seriesIdx, event.value);
        });

        const sortedTimes = Array.from(eventsByTime.keys()).sort(
          (a, b) => a - b,
        );

        sortedTimes.forEach((time) => {
          newChartData[0].push(time);
          const updates = eventsByTime.get(time)!;

          for (let j = 1; j < sCount; j++) {
            if (updates.has(j)) {
              newChartData[j].push(updates.get(j)!);
            } else {
              newChartData[j].push(null);
            }
          }
        });

        chartData = newChartData;
        chartInstance.setData(chartData as AlignedData);
        setDataTick((t) => t + 1);
      },
      { defer: true },
    ),
  );

  createEffect(
    on(
      () => props.currentTime,
      (currTime) => {
        if (currTime === 0 || !chartInstance || props.selectedData.length === 0)
          return;

        const sCount = props.selectedData.length + 1;
        const batch = props.latestBatch;

        if (!props.historicalData || props.historicalData.length === 0) {
          chartData = Array(sCount)
            .fill(null)
            .map(() => []);
        }

        const eventsByTime = new Map<number, Map<number, number>>();

        batch.forEach((event) => {
          const seriesIdx = idToSeriesIndex.get(event.id);

          if (seriesIdx === undefined) return;

          if (!eventsByTime.has(event.time)) {
            eventsByTime.set(event.time, new Map());
          }
          eventsByTime.get(event.time)!.set(seriesIdx, event.value);
        });

        const sortedTimes = Array.from(eventsByTime.keys()).sort(
          (a, b) => a - b,
        );

        sortedTimes.forEach((time) => {
          chartData[0].push(time);

          const updates = eventsByTime.get(time)!;
          for (let j = 1; j < sCount; j++) {
            if (updates.has(j)) {
              chartData[j].push(updates.get(j)!);
            } else {
              chartData[j].push(null);
            }
          }
        });

        const lastIdx = chartData[0].length - 1;
        const lastTime = lastIdx >= 0 ? chartData[0][lastIdx] : -1;

        if (currTime > (lastTime as number)) {
          chartData[0].push(currTime);
          for (let j = 1; j < sCount; j++) {
            let lastKnownValue: number | null = null;
            for (let k = chartData[j].length - 1; k >= 0; k--) {
              if (chartData[j][k] !== null) {
                lastKnownValue = chartData[j][k];
                break;
              }
            }
            chartData[j].push(lastKnownValue);
          }
        }

        chartInstance.setData(chartData as AlignedData);
        setDataTick((t) => t + 1);

        if (!isUserZoomed) {
          chartInstance.setScale("x", {
            min: Math.max(0, currTime - WINDOW_TIME),
            max: currTime,
          });
        }
      },
      { defer: true },
    ),
  );

  return (
    <div class="w-full h-full min-h-[250px] flex flex-row flex-1 bg-[var(--bg)] text-[var(--fg)] overflow-hidden">
      <div class="flex-1 min-w-0 flex flex-col relative">
        <div
          ref={chartRef}
          class="flex-1 w-full h-full"
          title="Drag to zoom | Shift+Drag or Middle-click to pan | Wheel to zoom | Double-click to reset"
        />
        <button
          onClick={() => setShowLegend(!showLegend())}
          class="absolute top-2 right-2 z-10 p-1.5 bg-[var(--sidebar-bg)] hover:bg-[var(--sidebar-active-bg)] border border-[var(--border)] rounded text-[var(--fg)] shadow-sm backdrop-blur-sm transition-all opacity-80 hover:opacity-100"
          title="Toggle Legend"
        >
          <Show when={showLegend()} fallback={<FiList class="size-3.5" />}>
            <FiChevronRight class="size-3.5" />
          </Show>
        </button>
      </div>
      <Show when={showLegend()}>
        <div class="w-60 flex flex-col border-l border-[var(--border)] bg-[var(--sidebar-bg)] shrink-0 overflow-hidden">
          <div class="px-3 pt-3 pb-2 border-b border-[var(--border-light)] bg-[var(--sidebar-bg)] shrink-0 z-10">
            <span class="text-[10px] font-bold uppercase tracking-wider">
              Legend ({props.selectedData.length})
            </span>
          </div>

          <div class="flex-1 overflow-y-auto p-2 flex flex-col gap-1 custom-scrollbar">
            <For each={props.selectedData}>
              {(item: any, idx) => {
                const seriesIdx = idx() + 1;
                const color = COLORS[idx() % COLORS.length];
                const isHidden = () => hiddenSeries().has(seriesIdx);

                const displayValue = () => {
                  dataTick();
                  const currIdx = hoverIdx();
                  const sData = chartData[seriesIdx];

                  if (!sData || sData.length === 0) return "-";

                  let val: number | null | undefined = null;
                  let startSearchIdx =
                    currIdx !== null ? currIdx : sData.length - 1;

                  for (let i = startSearchIdx; i >= 0; i--) {
                    if (sData[i] != null) {
                      val = sData[i];
                      break;
                    }
                  }

                  return typeof val === "number"
                    ? val.toFixed(1)
                    : (val ?? "-");
                };

                return (
                  <div
                    class={`flex items-start gap-2 p-1.5 cursor-pointer transition-all hover:bg-[var(--sidebar-active-bg)] rounded-sm border border-transparent hover:border-[var(--border-light)] ${
                      isHidden() ? "opacity-40 grayscale" : "opacity-100"
                    }`}
                    onClick={() => toggleSeries(seriesIdx)}
                    title="Click to toggle visibility"
                  >
                    <div class="relative flex items-center justify-center w-3 h-3 shrink-0 mt-[3px]">
                      <div
                        class="absolute w-full rounded-full"
                        style={{
                          height: item.isEstim ? "0px" : "3px",
                          "background-color": item.isEstim
                            ? "transparent"
                            : color,
                          "border-top": item.isEstim
                            ? `2px dashed ${color}`
                            : "none",
                        }}
                      />
                    </div>

                    <div class="flex flex-col flex-1 min-w-0 leading-tight">
                      <div class="flex items-center justify-between gap-1 mb-0.5">
                        <span class="font-bold text-[11px] text-[var(--title-color)] truncate flex items-center gap-1">
                          {item.kind || "VAR"}
                          <Show when={item.isEstim}>
                            <span class="text-[8px] bg-purple-500/20 text-purple-400 px-1 rounded-sm border border-purple-500/30 leading-none py-[2px]">
                              ESTIM
                            </span>
                          </Show>
                        </span>
                        <span class="font-mono text-[12px] font-bold text-[var(--fg)] tracking-tight">
                          {displayValue()}
                        </span>
                      </div>

                      <div
                        class="text-[10px] text-[var(--fg)] opacity-90 truncate"
                        title={item.equipmentId || item.id}
                      >
                        {item.equipmentId || item.id}
                      </div>

                      <div class="flex items-center gap-1.5 mt-1 text-[8.5px]">
                        <Show when={item.side}>
                          <span class="px-1 py-0.5 bg-[var(--pre-bg)] border border-[var(--border-light)] rounded-[2px] text-[var(--icons)] whitespace-nowrap">
                            Side: {item.side}
                          </span>
                        </Show>
                        <Show when={item.voltage_level}>
                          <span class="px-1 py-0.5 bg-[var(--pre-bg)] border border-[var(--border-light)] rounded-[2px] text-[var(--icons)] whitespace-nowrap">
                            {item.voltage_level}
                          </span>
                        </Show>
                        <span class="font-mono text-[var(--icons)] opacity-80 truncate">
                          {item.topic || "no-topic"}
                        </span>
                        <Show when={item.substation}>
                          <span class="ml-auto text-[var(--icons)] opacity-60 truncate max-w-[60px] text-right">
                            {item.substation}
                          </span>
                        </Show>
                      </div>
                    </div>
                  </div>
                );
              }}
            </For>
          </div>
        </div>
      </Show>
    </div>
  );
};
