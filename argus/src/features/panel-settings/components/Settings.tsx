/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createMemo, onMount, For, Show } from "solid-js";
import { FiSettings, FiCode, FiInfo } from "solid-icons/fi";
import { Tooltip } from "@kobalte/core/tooltip";

import { useSettings } from "../hooks/useSettings";
import { SETTINGS } from "@/config/settings";
import { SettingItem } from "./SettingItem";
import type { SettingFieldDefinition } from "../types";

export function Settings() {
  const { settings, savingKey, error, loadSettings, updateSettingPath } =
    useSettings();

  const [activeSectionId, setActiveSectionId] = createSignal<string>("network");
  const [searchQuery, _] = createSignal("");
  const [viewJsonMode, setViewJsonMode] = createSignal(false);

  onMount(() => {
    loadSettings();
  });

  const filteredSections = createMemo(() => {
    const q = searchQuery().trim().toLowerCase();
    if (!q) return SETTINGS;

    return SETTINGS.map((section) => {
      const titleMatch = section.title.toLowerCase().includes(q);
      const matchedFields = section.fields.filter(
        (f: SettingFieldDefinition) =>
          titleMatch ||
          f.label.toLowerCase().includes(q) ||
          f.key.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q),
      );
      return {
        ...section,
        fields: matchedFields,
      };
    }).filter((section) => section.fields.length > 0);
  });

  const currentSection = createMemo(() => {
    const current = filteredSections().find((s) => s.id === activeSectionId());
    return current ?? filteredSections()[0];
  });

  const getFieldValue = (sectionId: string, fieldKey: string) => {
    const current = settings() as Record<string, any>;
    if (sectionId === "network") {
      // Direct root fields for network (proxy, no_proxy)
      return current[fieldKey];
    }
    // Sub-objects for other sections (e.g. editor.fontSize)
    return current[sectionId]?.[fieldKey];
  };

  const handleUpdate = (sectionId: string, fieldKey: string, val: any) => {
    const path = sectionId === "network" ? [fieldKey] : [sectionId, fieldKey];
    return updateSettingPath(path, val);
  };

  return (
    <div class="flex h-full w-full bg-[var(--bg)] text-[var(--fg)] font-sans antialiased select-none">
      <aside class="w-60 shrink-0 border-r border-[var(--border)] bg-[var(--sidebar-bg)] flex flex-col justify-between">
        <div class="flex flex-col flex-1 min-h-0">
          <div class="h-10 px-4 border-b border-[var(--border)] flex items-center justify-between text-[13px] font-semibold text-[var(--title-color)]">
            <div class="flex items-center gap-2">
              <FiSettings class="w-4 h-4 text-[var(--sidebar-active)]" />
              <span>Settings</span>
            </div>
            <button
              onClick={() => setViewJsonMode(!viewJsonMode())}
              title={viewJsonMode() ? "GUI Settings" : "JSON Preview"}
              class={`p-1 rounded text-xs transition-colors ${
                viewJsonMode()
                  ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active)]"
                  : "text-[var(--sidebar-fg)] hover:text-[var(--fg)] hover:bg-[var(--media-bg)]"
              }`}
            >
              <FiCode class="w-3.5 h-3.5" />
            </button>
          </div>

          <nav class="flex-1 overflow-y-auto p-2 space-y-0.5">
            <For each={filteredSections()}>
              {(section) => {
                const isActive = () => currentSection()?.id === section.id;
                return (
                  <button
                    onClick={() => setActiveSectionId(section.id)}
                    class={`w-full text-left px-2.5 py-1.5 rounded text-xs transition-colors flex items-center justify-between group ${
                      isActive() && !viewJsonMode()
                        ? "bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active)] font-medium"
                        : "text-[var(--sidebar-fg)] hover:bg-[var(--media-bg)] hover:text-[var(--fg)]"
                    }`}
                  >
                    <div class="flex items-center gap-2">
                      <span>{section.title}</span>
                    </div>
                    <span class="text-[10px] text-[var(--sidebar-non-existant)] font-mono">
                      {section.fields.length}
                    </span>
                  </button>
                );
              }}
            </For>
          </nav>
        </div>
      </aside>

      <main class="flex-1 flex flex-col min-w-0 bg-[var(--bg)] overflow-hidden">
        <Show when={error()}>
          <div class="px-4 py-2 bg-red-500/10 border-b border-red-500/20 text-xs text-red-400">
            {error()}
          </div>
        </Show>

        <Show
          when={!viewJsonMode()}
          fallback={
            <div class="flex-1 flex flex-col overflow-hidden">
              <div class="h-10 px-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--table-header-bg)] text-xs text-[var(--sidebar-fg)]">
                <span class="font-mono">settings.json (raw)</span>
                <span class="text-[11px] text-[var(--sidebar-non-existant)]">
                  Read-only view
                </span>
              </div>
              <pre class="flex-1 p-4 font-mono text-xs overflow-auto text-[var(--fg)] bg-[var(--bg)] select-text">
                {JSON.stringify(settings(), null, 2)}
              </pre>
            </div>
          }
        >
          <Show
            when={currentSection()}
            fallback={
              <div class="p-8 text-center text-xs text-[var(--sidebar-non-existant)]">
                No matching settings found.
              </div>
            }
          >
            {(sec) => (
              <div class="flex-1 flex flex-col min-w-0 overflow-y-auto">
                <header class="py-2 px-4 h-10 border-b border-[var(--border)] bg-sidebar-bg shrink-0 flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <h2 class="text-sm font-semibold text-[var(--title-color)]">
                      {sec().title}
                    </h2>
                    <Show when={sec().description}>
                      <Tooltip>
                        <Tooltip.Trigger class="text-[var(--sidebar-non-existant)] hover:text-[var(--fg)] transition-colors p-0.5 rounded cursor-help outline-none">
                          <FiInfo class="w-3.5 h-3.5" />
                        </Tooltip.Trigger>
                        <Tooltip.Portal>
                          <Tooltip.Content class="z-50 max-w-xs px-2.5 py-1.5 text-xs text-sidebar-fg bg-sidebar-bg border border-border shadow-md rounded-sm outline-none data-expanded:animate-in data-closed:animate-out data-expanded:fade-in-0 data-closed:fade-out-0">
                            <Tooltip.Arrow class="fill-border" size={10} />
                            <span>{sec().description}</span>
                          </Tooltip.Content>
                        </Tooltip.Portal>
                      </Tooltip>
                    </Show>
                  </div>
                </header>

                <div class="divide-y divide-[var(--border)]">
                  <For each={sec().fields}>
                    {(field) => {
                      const fieldPathStr =
                        sec().id === "network"
                          ? field.key
                          : `${sec().id}.${field.key}`;
                      return (
                        <SettingItem
                          field={field}
                          sectionId={sec().id}
                          value={getFieldValue(sec().id, field.key)}
                          isSaving={savingKey() === fieldPathStr}
                          onUpdate={(val) =>
                            handleUpdate(sec().id, field.key, val)
                          }
                        />
                      );
                    }}
                  </For>
                </div>
              </div>
            )}
          </Show>
        </Show>
      </main>
    </div>
  );
}
