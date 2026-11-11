/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  type Component,
  Switch,
  Match,
  Show,
  createMemo,
  createSignal,
} from "solid-js";
import {
  FaSolidSpinner,
  FaSolidTriangleExclamation,
  FaSolidCircleCheck,
  FaSolidChevronDown,
  FaSolidCheck,
  FaSolidGear,
} from "solid-icons/fa";
import { Select } from "@kobalte/core/select";
import { Popover } from "@kobalte/core/popover";
import { Effect } from "effect";
import { HergeClient, HergeClientLive } from "@/services/herge";
import { useHerge } from "../hooks/useHerge";

interface HergeHeaderProps {
  currentUrl?: string;
}

export const HergeHeader: Component<HergeHeaderProps> = (props) => {
  const ctx = useHerge();

  const isBusy = () => ctx.legendLoading() || ctx.loading();
  const hasError = () => !!ctx.legendError();

  const schemaOptions = createMemo(() => [
    { value: "ALL", label: "TOUS LES SCHÉMAS" },
    ...ctx.schemasList().map((name) => ({ value: name, label: name })),
  ]);

  const currentOption = createMemo(
    () =>
      schemaOptions().find(
        (opt) => opt.value === (ctx.selectedSchema() ?? "ALL"),
      ) || schemaOptions()[0],
  );

  const [isConfigOpen, setIsConfigOpen] = createSignal(false);
  const [urlInput, setUrlInput] = createSignal(props.currentUrl || "");
  const [isSaving, setIsSaving] = createSignal(false);

  const handleSaveUrl = () => {
    const cleanUrl = urlInput().trim();
    if (!cleanUrl) return;

    setIsSaving(true);

    const updateProgram = Effect.gen(function* () {
      const herge = yield* HergeClient;
      yield* herge.setUrl(cleanUrl);
      console.log("URL mise à jour avec succès :", cleanUrl);
    }).pipe(
      Effect.catchAll((error) => {
        console.error("Échec du changement d'URL:", error);
        return Effect.void;
      }),
    );

    Effect.runPromise(Effect.provide(updateProgram, HergeClientLive)).then(
      () => {
        setIsSaving(false);
        setIsConfigOpen(false);
      },
    );
  };

  return (
    <header class="flex items-center justify-between px-5 py-2.5 bg-sidebar-bg border-b border-border shrink-0 gap-3 h-9">
      <div class="flex items-center gap-3.5">
        <div class="flex items-center ml-5 bg-(--sidebar-active-bg) border border-(--sidebar-active)/30 rounded-md transition-shadow focus-within:ring-2 focus-within:ring-links h-6">
          <Select
            options={schemaOptions()}
            value={currentOption()}
            optionValue="value"
            optionTextValue="label"
            onChange={(opt) => {
              if (!opt || opt.value === "ALL") {
                ctx.setSelectedSchema(null);
              } else {
                ctx.setSelectedSchema(opt.value);
              }
            }}
            itemComponent={(itemProps) => (
              <Select.Item
                item={itemProps.item}
                class="flex items-center justify-between px-3 py-2 text-xs text-fg cursor-pointer hover:bg-(--theme-hover) outline-none data-selected:text-links data-selected:bg-(--theme-hover) transition-colors rounded-sm mx-1"
              >
                <Select.ItemLabel>
                  {itemProps.item.rawValue.label}
                </Select.ItemLabel>
                <Select.ItemIndicator>
                  <FaSolidCheck size={12} class="text-links" />
                </Select.ItemIndicator>
              </Select.Item>
            )}
          >
            <Select.Trigger class="bg-transparent text-links border-none py-1.5 pl-2.5 pr-1.5 font-semibold text-[13px] cursor-pointer outline-none flex items-center gap-2">
              <Select.Value<{ value: string; label: string }>>
                {(state) => state.selectedOption()?.label ?? "TOUS LES SCHÉMAS"}
              </Select.Value>
              <Select.Icon class="opacity-70 mt-0.5">
                <FaSolidChevronDown size={10} />
              </Select.Icon>
            </Select.Trigger>

            <Select.Portal>
              <Select.Content class="bg-popover-bg border border-popover-border shadow-(--popover-shadow) rounded-md py-1.5 z-1050 animate-in fade-in zoom-in-95 min-w-50">
                <Select.Listbox class="outline-none max-h-75 overflow-y-auto scrollbar-hide" />
              </Select.Content>
            </Select.Portal>
          </Select>

          <Show when={ctx.selectedSchema()}>
            <button
              class="bg-transparent border-none text-links opacity-70 hover:opacity-100 cursor-pointer px-2 py-1.5 flex items-center justify-center outline-none border-l border-(--sidebar-active)/20 ml-1"
              onClick={() => ctx.setSelectedSchema(null)}
              title="Réinitialiser la vue globale"
            >
              ✕
            </button>
          </Show>
        </div>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <span
          class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold whitespace-nowrap border transition-colors"
          classList={{
            "bg-warning-bg border-warning-border text-warning-icon": isBusy(),
            "bg-green-500/10 border-green-500/30 text-green-600 dark:text-green-400":
              !isBusy() && !hasError(),
            "bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400":
              hasError(),
          }}
        >
          <Switch
            fallback={
              <>
                <FaSolidCircleCheck class="text-xs" /> connecté
              </>
            }
          >
            <Match when={isBusy()}>
              <FaSolidSpinner class="text-xs animate-spin" /> chargement
            </Match>
            <Match when={hasError()}>
              <FaSolidTriangleExclamation class="text-xs" /> erreur réseau
            </Match>
          </Switch>
        </span>

        <Popover open={isConfigOpen()} onOpenChange={setIsConfigOpen}>
          <Popover.Trigger class="flex items-center justify-center w-7 h-7 rounded-full bg-media-bg border border-border text-icons hover:bg-(--theme-hover) hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-links data-expanded:bg-(--theme-hover) data-expanded:text-fg">
            <FaSolidGear size={12} />
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content class="z-50 w-80 rounded-md border border-popover-border bg-popover-bg p-4 shadow-md outline-none data-expanded:animate-in data-closed:animate-out data-[closed]:fade-out-0 data-[expanded]:fade-in-0 data-[closed]:zoom-out-95 data-[expanded]:zoom-in-95">
              <Popover.Arrow class="text-popover-border" />

              <div class="flex flex-col gap-3">
                <div class="flex flex-col">
                  <span class="text-[11px] font-bold text-fg uppercase tracking-wider">
                    Configuration ArcGIS
                  </span>
                  <span class="text-[11px] text-icons">
                    L'URL sera mise à jour à chaud.
                  </span>
                </div>

                <input
                  type="text"
                  value={urlInput()}
                  onInput={(e) => setUrlInput(e.currentTarget.value)}
                  placeholder="http://gis.example.org/arcgis/..."
                  disabled={isSaving()}
                  class="flex h-8 w-full rounded border border-border bg-media-bg px-2.5 py-1 text-xs text-fg shadow-sm transition-colors placeholder:text-icons focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-links disabled:cursor-not-allowed disabled:opacity-50"
                />

                <div class="flex justify-end gap-2 mt-1">
                  <button
                    onClick={() => setIsConfigOpen(false)}
                    disabled={isSaving()}
                    class="inline-flex items-center justify-center rounded text-xs font-medium transition-colors hover:bg-(--theme-hover) text-fg h-7 px-3 outline-none focus-visible:ring-1 focus-visible:ring-links disabled:opacity-50"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleSaveUrl}
                    disabled={isSaving() || !urlInput().trim()}
                    class="inline-flex items-center justify-center gap-1.5 rounded text-xs font-medium transition-colors bg-links text-white hover:opacity-90 h-7 px-3 outline-none focus-visible:ring-1 focus-visible:ring-offset-1 focus-visible:ring-links shadow-sm disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isSaving() && (
                      <FaSolidSpinner class="animate-spin" size={10} />
                    )}
                    {isSaving() ? "Enregistrement..." : "Appliquer"}
                  </button>
                </div>
              </div>
            </Popover.Content>
          </Popover.Portal>
        </Popover>
      </div>
    </header>
  );
};
