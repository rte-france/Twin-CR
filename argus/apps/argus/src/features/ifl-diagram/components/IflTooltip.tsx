/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Component, createSignal, Show } from "solid-js";
import { useIflContext } from "../hooks/useIflContext";
import { IflCharacteristics } from "./IflCharacteristics";
import { useAppMode } from "@/hooks/useAppMode";
import { Mode } from "@/services/app-mode";

export const IflTooltip: Component = () => {
  const ctx = useIflContext();
  const [mode] = useAppMode();
  const [flipped, setFlipped] = createSignal(false);

  const readOnly = () => mode() === Mode.Scada;

  return (
    <Show when={ctx.selected()}>
      {(item) => {
        const i = item();
        const isEdge = i.elementType === "edge";
        const displayFrom = () => isEdge ? (flipped() ? i.to : i.from) : null;
        const displayTo = () => isEdge ? (flipped() ? i.from : i.to) : null;
        const title = () => isEdge
          ? `${displayFrom()} → ${displayTo()}`
          : i.nodeId;

        // Derive the effective PickInfo respecting flip
        const effectiveSelected = () => {
          const i = item();
          if (i.elementType === "node") return i;
          return { elementType: "edge" as const, from: displayFrom()!, to: displayTo()! };
        };

        return (
          <div class="absolute bottom-6 right-6 w-100 bg-surface/95 backdrop-blur-md border border-border text-text p-4 z-40 rounded-lg shadow-popout animate-in slide-in-from-bottom-5 max-h-[70vh] overflow-y-auto">
            <div class="flex justify-between items-start mb-2">
              <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded">
                {item().elementType}
              </span>
              <button
                onClick={() => ctx.setSelected(null)}
                class="text-icon hover:text-icon-hover transition-colors"
              >
                ✕
              </button>
            </div>

            <div class="flex items-center gap-2">
              <h3 class="text-sm font-semibold break-all leading-tight flex-1">
                {title()}
              </h3>
              <Show when={isEdge}>
                <button
                  class="text-xs text-text-muted hover:text-text border border-border rounded px-1.5 py-0.5 shrink-0"
                  title="Flip direction"
                  onClick={() => setFlipped((f) => !f)}
                >
                  ⇄
                </button>
              </Show>
            </div>

            <Show
              when={effectiveSelected()}
              keyed
            >
              {(sel) => (
                <IflCharacteristics
                  selected={sel}
                  readOnly={readOnly()}
                />
              )}
            </Show>
          </div>
        );
      }}
    </Show>
  );
};
