/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { onCleanup } from "solid-js";
import { Effect, Stream, Schedule, Ref } from "effect";
import { GmClient, GmHistoryItem, GmSseData } from "@/services/game-master/service";
import { EstimItem, ScadaClient, ScadaHistoryItem, ScadaSseData } from "@/services/scada/service";
import { TimeClient } from "@/services/time/service";
import { Mode } from "@/services/app-mode";
import { MappingItem } from "@/services/mapping/types";
import { systemRuntime } from "@/config/runtime";

export function useDynamicValues(
  getMappingItems: () => MappingItem[],
  getVisibleIds: () => Set<string>,
  applyBatchUpdate: (updates: Record<string, Record<string, number | null>>) => void,
) {
  let cancel: (() => void) | undefined;

  const start = (topics: string[], estimTopics: string[], currentMode: Mode) => {
    cancel?.();
    if (topics.length === 0 && estimTopics.length === 0) return;

    const program = Effect.gen(function* () {
      const gmClient = yield* GmClient;
      const scadaClient = yield* ScadaClient;
      const timeClient = yield* TimeClient;
      const client = currentMode === Mode.Scada ? scadaClient : gmClient;

      // Lookup: GmSseData.id -> { equipmentId, kind }
      const mappingById: Record<string, { equipmentId: string; kind: string; side: string | null }> = {};
      for (const item of getMappingItems()) {
        mappingById[item.id] = { equipmentId: item.equipmentId, kind: item.kind, side: item.side ?? null };
      }

      const buffer = yield* Ref.make<Record<string, Record<string, number | null>>>({});

      const writeMapping = (id: string, value: number) =>
        Ref.update(buffer, (prev) => {
          const mapping = mappingById[id];
          if (!mapping) return prev;
          if (!getVisibleIds().has(mapping.equipmentId)) return prev;
          const next = { ...prev };
          if (!next[mapping.equipmentId]) next[mapping.equipmentId] = {} as Record<string, number | null>;
          const field = `__dynamic_mapping__${mapping.kind}${mapping.side ? `__${mapping.side}` : ""}`;
          next[mapping.equipmentId] = { ...next[mapping.equipmentId], [field]: value };
          return next;
        });

      const writeEstim = (equipmentId: string, kind: string, side: string | null, value: number) =>
        Ref.update(buffer, (prev) => {
          if (!getVisibleIds().has(equipmentId)) return prev;
          const next = { ...prev };
          if (!next[equipmentId]) next[equipmentId] = {} as Record<string, number | null>;
          const field = `__dynamic_estim__${kind}${side ? `__${side}` : ""}`;
          next[equipmentId] = { ...next[equipmentId], [field]: value };
          return next;
        });

      const flush = Effect.gen(function* () {
        const updates = yield* Ref.getAndSet(buffer, {});
        if (Object.keys(updates).length > 0) applyBatchUpdate(updates);
      });

      const { current_time: now } = yield* timeClient.getTime;

      // Initial history fetch — mapping
      yield* Effect.all(
        topics.map((topic) =>
          client.get<(GmHistoryItem | ScadaHistoryItem)[]>(`/history/${topic}?min=${now - 10}&max=${now}`).pipe(
            Effect.flatMap((data) =>
              // last item per id wins (data sorted by time ascending)
              Effect.all(
                [...new Map(data.map((i) => [i.id, i])).values()]
                  .map((i) => writeMapping(i.id, i.value)),
                { concurrency: "unbounded" },
              )
            ),
            Effect.catchAll(() => Effect.void),
          )
        ),
        { concurrency: 5 },
      );

      // Initial history fetch — estim (only on Scada)
      if (currentMode === Mode.Scada) {
        yield* Effect.all(
          estimTopics.map((topic) =>
            scadaClient.get<EstimItem[]>(`/history-estim/${topic}?min=${now - 600}&max=${now}`).pipe(
              Effect.flatMap((data) => {
                // last item per equipmentId+kind wins
                const latest = new Map<string, EstimItem>();
                for (const item of data) {
                  latest.set(`${item.equipmentId}__${item.kind}__${item.side ?? ""}`, item);
                }
                return Effect.all(
                  [...latest.values()].map((i) => writeEstim(i.equipmentId, i.kind, i.side, i.value)),
                  { concurrency: "unbounded" },
                );
              }),
              Effect.catchAll(() => Effect.void),
            )
          ),
          { concurrency: 5 },
        );
      }

      yield* flush;

      // SSE subscriptions
      const subscribeMapping = Effect.all(
        topics.map((topic) =>
          Stream.runForEach(
            client.sseStream<GmSseData | ScadaSseData>(`/sub/${topic}`),
            (item) => writeMapping(item.id, item.value),
          ).pipe(Effect.catchAll(() => Effect.void))
        ),
        { concurrency: "unbounded" },
      );

      const subscribeEstim = currentMode === Mode.Scada
        ? Effect.all(
            estimTopics.map((topic) =>
              Stream.runForEach(
                scadaClient.sseStream<EstimItem>(`/sub-estim/${topic}`),
                (item) => writeEstim(item.equipmentId, item.kind, item.side, item.value),
              ).pipe(Effect.catchAll(() => Effect.void))
            ),
            { concurrency: "unbounded" },
          )
        : Effect.void;

      const flushLoop = Effect.repeat(flush, Schedule.spaced("1 second"));

      yield* Effect.all([subscribeMapping, subscribeEstim, flushLoop], {
        concurrency: "unbounded",
      });
    });

    cancel = systemRuntime.runCallback(
      program as Effect.Effect<void, never, GmClient | ScadaClient | TimeClient>
    );
  };

  const stop = () => cancel?.();
  onCleanup(stop);

  return { start, stop };
}
