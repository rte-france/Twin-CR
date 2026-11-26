/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createEffect,
  onMount,
  onCleanup,
  batch,
  Show,
  lazy,
  Suspense,
  type Component,
} from "solid-js";
import { Effect, Schedule, Stream } from "effect";
import { systemRuntime } from "@/config/runtime";
import { FiActivity, FiEdit3, FiX, FiLoader } from "solid-icons/fi";

import { GmClient, GmHistoryItem, GmSseData } from "@/services/game-master/service";
import { Mode } from "@/services/app-mode";
import { EstimItem, ScadaClient, ScadaHistoryItem, ScadaSseData } from "@/services/scada/service";
import { SelectionChart } from "./SelectionChart";
import { ChartDataRow, ChartService, getUniqueKey } from "@/services/chart";
import { makeBackendClient } from "@/services/http-client";
import { useAppMode } from "@/hooks/useAppMode";
import { SimulationTime } from "@/services/time";

/** An estimation history or live item, as a chart point. */
const estimPoint = (item: EstimItem): GmSseData => ({
  id: `${item.equipmentId}-${item.kind}-${item.side || ""}-estim`,
  value: item.value,
  time: item.time,
});

const ChartEditor = lazy(async () => {
  const module = await import("./ChartEditor");
  return { default: module.ChartEditor };
});

export interface CurveViewerProps {
  dashboardId: string;
  title?: string;
}

export const CurveViewer: Component<CurveViewerProps> = (props) => {
  const dId = () => props.dashboardId || "default";

  const [isEditorOpen, setIsEditorOpen] = createSignal(false);
  const [bucketCurves, setBucketCurves] = createSignal<ChartDataRow[]>([]);
  const [latestHistoryBatch, setLatestHistoryBatch] = createSignal<GmSseData[]>(
    [],
  );
  const [currentTime, setCurrentTime] = createSignal<number>(0);

  const [mode] = useAppMode();

  const loadSelection = () => {
    systemRuntime
      .runPromise(
        Effect.gen(function* () {
          const chartSvc = yield* ChartService;
          return yield* chartSvc.getSelection(dId());
        }),
      )
      .then(setBucketCurves);
  };

  const handleSelectionEvent = (e: Event) => {
    const customEvent = e as CustomEvent;
    if (
      !customEvent.detail ||
      customEvent.detail.chartId === dId() ||
      !customEvent.detail.chartId
    ) {
      loadSelection();
    }
  };

  onMount(() => {
    loadSelection();
    window.addEventListener("chart-selection-added", handleSelectionEvent);
    window.addEventListener("chart-selection-cleared", handleSelectionEvent);

    onCleanup(() => {
      window.removeEventListener("chart-selection-added", handleSelectionEvent);
      window.removeEventListener(
        "chart-selection-cleared",
        handleSelectionEvent,
      );
    });
  });

  createEffect(() => {
    const selectedItems = bucketCurves();
    const currentMode = mode();

    if (selectedItems.length === 0) return;

    const topics = [
      ...new Set(selectedItems.filter((i) => !i.isEstim).map((i) => i.topic)),
    ];
    const estimTopics = [
      ...new Set(selectedItems.filter((i) => i.isEstim).map((i) => i.topic)),
    ];

    const program = Effect.gen(function* () {
      const WINDOW_SIZE = 200;
      const HISTORY_BUFFER = 6 * 3600;

      // Same API as GmClient and ScadaClient, through the Argus HTTP client.
      const scada = makeBackendClient((yield* ScadaClient).getUrl);
      const client = currentMode === Mode.GameMaster
        ? makeBackendClient((yield* GmClient).getUrl)
        : scada;

      const selectedIds = new Set(selectedItems.map((item) => getUniqueKey(item)));
      const isSelected = (entry: GmSseData) => selectedIds.has(entry.id);

      /** Appends `entries` and drops the points older than the history buffer. */
      const appendToHistory = (entries: GmSseData[], now = currentTime()) =>
        setLatestHistoryBatch((prev) => {
          const minTime = now - WINDOW_SIZE - HISTORY_BUFFER;
          return [...prev, ...entries.filter(isSelected)].filter(
            (e) => e.time >= minTime,
          );
        });

      // Fetch historical data at startup
      const fetchInitialHistory = (now: number) => Effect.gen(function* () {
        const fetchMinTime = Math.max(0, now - WINDOW_SIZE - HISTORY_BUFFER);

        const fetchTasks: Effect.Effect<GmSseData[], never, never>[] = [
          ...topics.map((topic) =>
            client.get<(GmHistoryItem | ScadaHistoryItem)[]>(
              `/history/${topic}?min=${fetchMinTime}&max=${now}`,
            ).pipe(
              Effect.map((data) => data.map((item): GmSseData => ({
                id: item.id,
                value: item.value,
                time: "time" in item ? item.time : item.time_received,
              }))),
              Effect.catchAll(() => Effect.succeed([] as GmSseData[])),
            )
          ),
          ...estimTopics.map((topic) =>
            scada.get<EstimItem[]>(
              `/history-estim/${topic}?min=${fetchMinTime}&max=${now}`,
            ).pipe(
              Effect.map((data) => data.map(estimPoint)),
              Effect.catchAll(() => Effect.succeed([] as GmSseData[])),
            )
          ),
        ];

        yield* Effect.all(
          fetchTasks.map((task) =>
            task.pipe(Effect.tap((entries) => appendToHistory(entries, now))),
          ),
          { concurrency: 5 },
        );
      });

      // Subscribe to time stream to track current time.
      // The history is fetched at the first time received
      let historyLoaded = false;
      const trackTime = Stream.runForEach(
        client.sseStream<SimulationTime>("/time"),
        ({ current_time }) => Effect.gen(function* () {
          setCurrentTime(current_time);
          if (!historyLoaded) {
            historyLoaded = true;
            // Runs in the background as it takes quite some time
            yield* Effect.fork(fetchInitialHistory(current_time));
          }
        }),
      ).pipe(
        Effect.retry(Schedule.spaced("2 seconds")),
        Effect.catchAll(() => Effect.void),
      );

      // Subscribe to live SSE updates (except estim that is on a separate endpoint, see below)
      const subscribeTopics = Effect.all(
        topics.map((topic) =>
          Stream.runForEach(
            client.sseStream<GmSseData | ScadaSseData>(`/sub/${topic}`),
            (item) => Effect.sync(() =>
              appendToHistory([{
                id: item.id,
                value: item.value,
                time: "time" in item ? item.time : item.time_received,
              }])
            ),
          ).pipe(
            Effect.retry(Schedule.spaced("2 seconds")),
            Effect.catchAll(() => Effect.void),
          )
        ),
        { concurrency: "unbounded" },
      );

      // Subscribe to live SSE updates for estim
      const subscribeEstim = Effect.all(
        estimTopics.map((topic) =>
          Stream.runForEach(
            scada.sseStream<EstimItem>(`/sub-estim/${topic}`),
            (item) => Effect.sync(() => appendToHistory([estimPoint(item)])),
          ).pipe(
            Effect.retry(Schedule.spaced("2 seconds")),
            Effect.catchAll(() => Effect.void),
          )
        ),
        { concurrency: "unbounded" },
      );

      yield* Effect.all([trackTime, subscribeTopics, subscribeEstim], {
        concurrency: "unbounded",
      });
    });

    const typedProgram = program as Effect.Effect<
      void,
      never,
      GmClient | ScadaClient
    >;
    const cancel = systemRuntime.runCallback(typedProgram);

    onCleanup(() => {
      cancel();
      batch(() => {
        setLatestHistoryBatch([]);
        setCurrentTime(0);
      });
    });
  });

  return (
    <div class="relative flex flex-col w-full h-full bg-[var(--bg)] overflow-hidden">
      <div class="flex flex-col w-full h-full z-0">
        <div class="flex items-center gap-2 px-3 bg-[var(--sidebar-bg)] border-b border-[var(--divider)] h-9 shrink-0">
          <FiActivity class="size-4 text-[var(--links)]" />
          <span class="text-[10px] text-[var(--fg)] opacity-50 font-mono ml-2">
            {dId()}
          </span>
          <div class="flex-1" />
          <span class="text-xs text-[var(--fg)] opacity-70 mr-2">
            {bucketCurves().length} curves
          </span>
          <button
            onClick={() => setIsEditorOpen(true)}
            class="flex items-center gap-1 px-2 py-1 text-xs font-medium bg-[var(--media-bg)] hover:bg-[var(--sidebar-active-bg)] text-[var(--fg)] rounded transition-colors border border-[var(--border)]"
            title="Edit curves in bucket"
          >
            <FiEdit3 class="size-3" /> Edit
          </button>
        </div>

        <div class="flex-1 w-full overflow-hidden flex flex-col">
          {bucketCurves().length > 0 ? (
            <SelectionChart
              selectedData={bucketCurves()}
              latestBatch={latestHistoryBatch()}
              currentTime={currentTime()}
            />
          ) : (
            <div class="flex-1 flex items-center justify-center text-[var(--fg)] opacity-50 text-sm italic border border-dashed border-[var(--border)] rounded m-4">
              No curves in this bucket. Click "Edit" to add some.
            </div>
          )}
        </div>
      </div>

      <Show when={isEditorOpen()}>
        <div
          class="absolute inset-0 bg-black/20 backdrop-blur-[1px] transition-opacity animate-in fade-in duration-200"
          onClick={() => setIsEditorOpen(false)}
        />
      </Show>

      <div
        class={`absolute top-0 right-0 h-full w-full sm:w-[85%] max-w-[900px] bg-[var(--bg)] border-l border-[var(--border)] z-50 flex flex-col transform transition-transform duration-300 ease-in-out ${
          isEditorOpen() ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div class="flex items-center justify-between px-3 py-1.5 border-b border-[var(--border)] bg-[var(--sidebar-bg)] shrink-0 h-9">
          <h3 class="flex items-center gap-2 text-[11px] uppercase tracking-wider font-bold text-[var(--fg)] opacity-80">
            <FiActivity class="size-3.5" />
            Editing Chart
            <span class="font-mono text-[var(--links)] opacity-100 normal-case tracking-normal ml-1">
              [{props.title || dId()}]
            </span>
          </h3>
          <button
            onClick={() => setIsEditorOpen(false)}
            class="flex items-center justify-center p-1 text-[var(--icons)] hover:text-[var(--full-contrast)] hover:bg-[var(--icon-btn-bg-hover)] rounded-sm transition-colors"
            title="Close Editor"
          >
            <FiX class="size-4" />
          </button>
        </div>

        <div class="flex-1 w-full overflow-hidden relative bg-[var(--bg)]">
          <Show when={isEditorOpen()}>
            <Suspense
              fallback={
                <div class="flex flex-col items-center justify-center w-full h-full text-[var(--fg)] opacity-60 gap-3">
                  <FiLoader class="size-6 animate-spin text-[var(--links)]" />
                  <span class="text-[11px] font-mono uppercase tracking-widest font-bold animate-pulse">
                    Loading Data Grid Module...
                  </span>
                </div>
              }
            >
              <ChartEditor dashboardId={dId()} />
            </Suspense>
          </Show>
        </div>
      </div>
    </div>
  );
};
