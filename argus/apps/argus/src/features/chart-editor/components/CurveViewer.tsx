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
import { Effect, Schedule, Stream, Context } from "effect";
import { systemRuntime } from "@/config/runtime";
import { FiActivity, FiEdit3, FiX, FiLoader } from "solid-icons/fi";

import { GmClient, GmHistoryItem, GmSseData } from "@/services/game-master/service";
import { Mode } from "@/services/app-mode";
import { EstimItem, ScadaClient, ScadaHistoryItem } from "@/services/scada/service";
import { SelectionChart } from "./SelectionChart";
import { ChartDataRow, ChartService } from "@/services/chart";
import { useAppMode } from "@/hooks/useAppMode";

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

    const tmTsTopics = [
      ...new Set(selectedItems.filter((i) => !i.isEstim).map((i) => i.topic)),
    ];
    const estimTopics = [
      ...new Set(selectedItems.filter((i) => i.isEstim).map((i) => i.topic)),
    ];

    const program = Effect.gen(function* () {
      const WINDOW_SIZE = 200;
      const HISTORY_BUFFER = 3600;
      let lastTime = 0;

      const setupStream = (
        client:
          | Context.Tag.Service<typeof GmClient>
          | Context.Tag.Service<typeof ScadaClient>,
      ) => {
        return Effect.gen(function* () {
          const scada = yield* ScadaClient;
          const timeStream = client.sseStream<{ current_time: number }>(
            "/time",
          );

          yield* Stream.runForEach(timeStream, (timePayload) =>
            Effect.gen(function* () {
              const currTime = timePayload.current_time;
              if (currTime > lastTime) {
                const fetchMinTime = Math.max(
                  0,
                  currTime - WINDOW_SIZE - HISTORY_BUFFER,
                );
                const fetchTasks: Effect.Effect<GmSseData[], any, any>[] = [];

                for (const topic of tmTsTopics) {
                  fetchTasks.push(
                    client
                      .get<
                        any[]
                      >(`/history/${topic}?min=${fetchMinTime}&max=${currTime}`)
                      .pipe(
                        Effect.map((data) =>
                          data.map(
                            (item: GmHistoryItem | ScadaHistoryItem): GmSseData => ({
                              id: `${item.id}-tmts`,
                              value: item.value,
                              time: "time" in item ? item.time : item.time_received,
                            }),
                          ),
                        ),
                        Effect.catchAll(() =>
                          Effect.succeed([] as GmSseData[]),
                        ),
                      ),
                  );
                }

                for (const topic of estimTopics) {
                  fetchTasks.push(
                    scada
                      .get<
                        any[]
                      >(`/history-estim/${topic}?min=${fetchMinTime}&max=${currTime}`)
                      .pipe(
                        Effect.map((data) =>
                          data.map(
                            (item: EstimItem): GmSseData => ({
                              id: `${item.equipmentId}-${item.kind}-${item.side || ""}-estim`,
                              value: item.value,
                              time: item.time,
                            }),
                          ),
                        ),
                        Effect.catchAll(() =>
                          Effect.succeed([] as GmSseData[]),
                        ),
                      ),
                  );
                }

                const results = yield* Effect.all(fetchTasks, {
                  concurrency: 5,
                });

                const mergedBatch = results
                  .flat()
                  .sort((a, b) => a.time - b.time);

                yield* Effect.sync(() => {
                  batch(() => {
                    setLatestHistoryBatch(mergedBatch);
                    setCurrentTime(currTime);
                  });
                });

                lastTime = currTime;
              }
            }),
          );
        });
      };

      if (currentMode === Mode.GameMaster) {
        const client = yield* GmClient;
        yield* Effect.repeat(setupStream(client), Schedule.spaced("2 seconds"));
      } else if (currentMode === Mode.Scada) {
        const client = yield* ScadaClient;
        yield* Effect.repeat(setupStream(client), Schedule.spaced("2 seconds"));
      }
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
