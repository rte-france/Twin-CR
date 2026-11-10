/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, Component, createSignal, For } from "solid-js";
import { AiOutlineClose } from "solid-icons/ai";
import { FiSearch, FiChevronRight } from "solid-icons/fi";
import { Effect } from "effect";
import { systemRuntime } from "@/config/runtime";

import { SelectedActionItem } from "../hooks/useActionPanelSelection";
import { Chart } from "@/features/chart-editor/types";

import { MappingItem, MappingService } from "@/services/mapping";
import { ChartDataRow, ChartService } from "@/services/chart";
import { typeOf } from "@/services/network-properties";
import { SingleElementPopup } from "@/features/network-properties-viewer/components/SingleElementPopup";

interface Props {
  SelectedActionItem: SelectedActionItem;
  onClose: () => void;
}

export const SldActionPanel: Component<Props> = (props) => {
  const [showChartDropdown, setShowChartDropdown] = createSignal(false);
  const [chartSearchQuery, setChartSearchQuery] = createSignal("");
  const [availableCharts, setAvailableCharts] = createSignal<Chart[]>([]);

  const [isLoadingMapping, setIsLoadingMapping] = createSignal(false);
  const [matchingCurves, setMatchingCurves] = createSignal<MappingItem[]>([]);
  const [selectedCurveIds, setSelectedCurveIds] = createSignal<string[]>([]);

  const [propertiesPopupOpen, setPropertiesPopupOpen] = createSignal(false);
  const [componentType, setComponentType] = createSignal<string | null>(null);

  const handleOpenPropertiesPopup = async () => {
    if (!props.SelectedActionItem) return;
    const type = await typeOf(props.SelectedActionItem.equipmentId);
    if (!type) {
      console.error("Failed to fetch component type of", props.SelectedActionItem.equipmentId);
      return;
    }
    setComponentType(type);
    setPropertiesPopupOpen(true);
  };

  const loadAvailableCharts = () => {
    const stored = localStorage.getItem("chart_dashboards");
    if (stored) {
      try {
        setAvailableCharts(JSON.parse(stored) as Chart[]);
      } catch (e) {
        setAvailableCharts([]);
      }
    }
  };

  const handleAddToChartClick = (e: MouseEvent) => {
    e.stopPropagation();
    loadAvailableCharts();

    if (!showChartDropdown()) {
      setIsLoadingMapping(true);
      setShowChartDropdown(true);

      systemRuntime
        .runPromise(
          Effect.gen(function* () {
            const mappingSvc = yield* MappingService;
            yield* mappingSvc.fetch();
            const state = yield* mappingSvc.getState;
            return state.data as MappingItem[];
          }),
        )
        .then((allData) => {
          const matches = allData.filter(
            (m) =>
              m.equipmentId === props.SelectedActionItem?.equipmentId
          );
          setMatchingCurves(matches);
          const autoSelected: string[] = [];
          matches.forEach((m) => autoSelected.push(m.id));

          setSelectedCurveIds(autoSelected);
          setIsLoadingMapping(false);
        });
    } else {
      setShowChartDropdown(false);
    }
  };

  const toggleCurve = (id: string, checked: boolean) => {
    if (checked) setSelectedCurveIds((prev) => [...prev, id]);
    else setSelectedCurveIds((prev) => prev.filter((x) => x !== id));
  };

  const toggleAllCurves = () => {
    if (selectedCurveIds().length === matchingCurves().length) {
      setSelectedCurveIds([]);
    } else {
      setSelectedCurveIds(matchingCurves().map((c) => c.id));
    }
  };

  const addToSpecificChart = (chartId: string) => {
    const itemsToAdd = matchingCurves().filter((m) =>
      selectedCurveIds().includes(m.id),
    );
    if (itemsToAdd.length === 0) return;

    systemRuntime
      .runPromise(
        Effect.gen(function* () {
          const chartSvc = yield* ChartService;

          const convertedItems: ChartDataRow[] = itemsToAdd.map((m) => ({
            id: m.id,
            topic: m.topic,
            factor: m.factor,
            equipmentId: m.equipmentId,
            kind: m.kind,
            voltage_level: m.voltage_level,
            substation: m.substation,
          }));

          const existingData = yield* chartSvc.getSelection(chartId);
          const merged = [...existingData, ...convertedItems];

          const unique = Array.from(
            new Map(merged.map((item) => [item.id, item])).values(),
          );

          yield* chartSvc.setSelection(chartId, unique);

          const event = new CustomEvent("chart-selection-added", {
            detail: {
              chartId: chartId,
              addedItems: convertedItems,
            },
          });
          window.dispatchEvent(event);
        }),
      )
      .then(() => {
        setShowChartDropdown(false);
        setChartSearchQuery("");
        props.onClose();
      });
  };

  const filteredCharts = () =>
    availableCharts().filter((c) =>
      c.name.toLowerCase().includes(chartSearchQuery().toLowerCase()),
    );

  return (
    <Show when={props.SelectedActionItem}>
      <div
        data-action-panel
        class="absolute top-2 left-2 z-20 w-[260px] bg-[var(--popover-bg)] p-2 text-[var(--fg)] flex flex-col gap-2 transition-all duration-200 animate-in fade-in slide-in-from-top-1 shadow-[var(--popover-shadow)] rounded-md border border-[var(--popover-border)]"
        onClick={(e) => e.stopPropagation()}
        onContextMenu={(e) => e.preventDefault()}
      >
        <div class="flex items-center justify-between pb-1 mb-0.5 border-b border-[var(--divider)]">
          <h3 class="text-xs font-semibold text-[var(--title-color)] uppercase tracking-tight">
            {props.SelectedActionItem!.equipmentId}
          </h3>
          <button
            onClick={props.onClose}
            class="p-0.5 rounded-sm hover:bg-[var(--icon-btn-bg-hover)] text-[var(--icons)] hover:text-[var(--icons-hover)] transition-colors cursor-pointer"
          >
            <AiOutlineClose size={14} />
          </button>
        </div>

        <Show when={props.SelectedActionItem!.side}>
          <div class="text-[11px] leading-none font-mono text-[var(--code-text)] bg-[var(--pre-bg)] p-2 rounded-sm border border-[var(--divider)] flex justify-between items-center gap-2 mt-1">
            <span class="text-[var(--icons)] select-none">Side</span>
            <span class="truncate">{props.SelectedActionItem!.side}</span>
          </div>
        </Show>

        <button
          onClick={() => handleOpenPropertiesPopup()}
          class="w-full text-left px-2 py-1.5 text-[11px] bg-[var(--media-bg)] border border-[var(--border-light)] hover:border-[var(--links)] text-[var(--fg)] rounded-sm transition-colors cursor-pointer flex items-center justify-between font-medium"
        >
          Properties
        </button>

        <div class="flex flex-col gap-1 mt-1 relative">
          <button
            onClick={(e) =>
              handleAddToChartClick(e)
            }
            class="w-full text-left px-2 py-1.5 text-[11px] bg-[var(--media-bg)] border border-[var(--border-light)] hover:border-[var(--links)] text-[var(--fg)] rounded-sm transition-colors cursor-pointer flex items-center justify-between font-medium"
          >
            <span>Add to Chart</span>
            <FiChevronRight
              class={`transition-transform duration-200 ${
                showChartDropdown()
                  ? "rotate-90 text-[var(--links)]"
                  : "text-[var(--icons)]"
              }`}
            />
          </button>

          <Show when={showChartDropdown()}>
            <div class="absolute left-full top-0 ml-2 w-[280px] bg-[var(--popover-bg)] border border-[var(--border)] shadow-[var(--popover-shadow)] rounded-md z-50 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-100">
              {/* ÉTAPE 1 : SÉLECTION DES COURBES */}
              <div class="flex items-center justify-between px-2 py-2 bg-[var(--sidebar-bg)] border-b border-[var(--border-light)]">
                <span class="text-[10px] font-bold text-[var(--title-color)] uppercase tracking-wider">
                  1. Variables ({matchingCurves().length})
                </span>
                <Show when={matchingCurves().length > 0}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleAllCurves();
                    }}
                    class="text-[9px] font-medium text-[var(--sidebar-fg)] hover:text-[var(--links)] uppercase transition-colors"
                  >
                    {selectedCurveIds().length === matchingCurves().length
                      ? "Deselect All"
                      : "Select All"}
                  </button>
                </Show>
              </div>

              <div class="max-h-[140px] overflow-y-auto custom-scrollbar flex flex-col bg-[var(--popover-bg)]">
                <Show when={isLoadingMapping()}>
                  <div class="p-3 text-[10px] opacity-70 italic text-[var(--fg)] text-center">
                    Loading mapping...
                  </div>
                </Show>

                <Show
                  when={
                    !isLoadingMapping() && matchingCurves().length === 0
                  }
                >
                  <div class="p-3 text-[10px] opacity-70 italic text-[var(--fg)] text-center">
                    No mapping found for this EqID.
                  </div>
                </Show>

                <For each={matchingCurves()}>
                  {(curve) => (
                    <label class="flex items-start gap-2 p-1.5 cursor-pointer hover:bg-[var(--sidebar-active-bg)] border-b border-[var(--divider)] last:border-0 transition-colors group">
                      <input
                        type="checkbox"
                        class="accent-[var(--links)] shrink-0 mt-[3px]"
                        checked={selectedCurveIds().includes(curve.id)}
                        onInput={(e) =>
                          toggleCurve(curve.id, e.currentTarget.checked)
                        }
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div class="flex flex-col flex-1 min-w-0 leading-tight">
                        <div class="flex items-center justify-between gap-1">
                          <span class="font-semibold text-[11px] text-[var(--fg)] truncate group-hover:text-[var(--links)] transition-colors">
                            {curve.kind || "Unknown"}
                          </span>
                          <Show when={curve.voltage_level}>
                            <span class="text-[8.5px] px-1 py-0.5 bg-[var(--pre-bg)] border border-[var(--border-light)] rounded-[2px] text-[var(--icons)] whitespace-nowrap">
                              {curve.voltage_level}
                            </span>
                          </Show>
                        </div>
                        <div class="flex items-center justify-between gap-1 mt-0.5">
                          <span class="text-[9.5px] font-mono text-[var(--icons)] truncate">
                            {curve.topic}
                          </span>
                          <Show when={curve.substation}>
                            <span class="text-[9px] opacity-60 text-[var(--icons)] truncate max-w-[80px] text-right">
                              {curve.substation}
                            </span>
                          </Show>
                        </div>
                      </div>
                    </label>
                  )}
                </For>
              </div>

              <div class="flex items-center justify-between px-2 py-2 bg-[var(--sidebar-bg)] border-y border-[var(--border-light)] mt-1">
                <span class="text-[10px] font-bold text-[var(--title-color)] uppercase tracking-wider">
                  2. Destination
                </span>
              </div>

              <div class="p-1 border-b border-[var(--divider)] bg-[var(--popover-bg)]">
                <div class="relative flex items-center">
                  <FiSearch class="absolute left-2 size-3 text-[var(--icons)]" />
                  <input
                    type="text"
                    placeholder="Search dashboard..."
                    value={chartSearchQuery()}
                    onInput={(e) =>
                      setChartSearchQuery(e.currentTarget.value)
                    }
                    onClick={(e) => e.stopPropagation()}
                    class="w-full pl-7 pr-2 py-1.5 text-[10px] bg-[var(--pre-bg)] border border-[var(--pre-border)] rounded focus:outline-none focus:border-[var(--links)] text-[var(--fg)]"
                  />
                </div>
              </div>

              <div class="max-h-[140px] overflow-y-auto custom-scrollbar flex flex-col bg-[var(--popover-bg)]">
                <For each={filteredCharts()}>
                  {(chart) => (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        addToSpecificChart(chart.id);
                      }}
                      disabled={selectedCurveIds().length === 0}
                      class="flex flex-col flex-1 min-w-0 p-1.5 hover:bg-[var(--sidebar-active-bg)] border-b border-[var(--divider)] last:border-0 transition-colors text-left disabled:opacity-40 disabled:cursor-not-allowed group w-full"
                    >
                      <div class="flex items-center justify-between w-full gap-2">
                        <span class="font-semibold text-[11px] text-[var(--fg)] truncate group-hover:text-[var(--links)] transition-colors">
                          {chart.name}
                        </span>
                      </div>
                      <Show when={chart.topic}>
                        <span class="text-[9.5px] font-mono text-[var(--icons)] truncate mt-0.5">
                          {chart.topic}
                        </span>
                      </Show>
                    </button>
                  )}
                </For>
                <Show when={filteredCharts().length === 0}>
                  <div class="p-3 text-center text-[10px] opacity-50 text-[var(--fg)] italic">
                    No dashboards found
                  </div>
                </Show>
              </div>
            </div>
          </Show>
        </div>

        <Show when={propertiesPopupOpen() && componentType()}>
          <SingleElementPopup
            open={propertiesPopupOpen()}
            onClose={() => setPropertiesPopupOpen(false)}
            elementId={props.SelectedActionItem!.equipmentId}
            componentType={componentType()!}
          />
        </Show>
      </div>
    </Show>
  );
};
