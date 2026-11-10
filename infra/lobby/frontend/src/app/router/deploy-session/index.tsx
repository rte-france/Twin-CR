/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { type Component, For, Show, createResource } from "solid-js";
import { useSearchParams, A } from "@solidjs/router";
import { FiSettings, FiEdit2, FiPlay, FiServer, FiLayers } from "solid-icons/fi";
import { SessionAPI } from "@/features/session";

export const DeploySession: Component = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [templates] = createResource(SessionAPI.fetchTemplates);

  const selectedId = () => {
    const t = searchParams.template;
    const idFromUrl = Array.isArray(t) ? t[0] : t;
    return idFromUrl || templates()?.[0]?.id;
  };
  const [templateDetails] = createResource(selectedId, (id) => SessionAPI.fetchTemplateDetails(id));

  return (
    <div class="flex h-full gap-4">
      <aside class="w-1/4 min-w-70 flex flex-col">
        <div class="flex-1 min-h-0 flex flex-col h-full bg-white text-slate-800 font-sans select-none border border-slate-200 rounded-md overflow-hidden shadow-sm">
          <div class="p-4 space-y-4 border-b border-slate-200 bg-slate-50 shrink-0">
            <div class="flex items-center justify-between text-xs text-slate-500">
              <span class="font-medium uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                <FiLayers class="size-3.5" /> Group x Template
              </span>
              <span class="font-medium">
                {templates()?.length || 0} template{(templates()?.length || 0) > 1 ? "s" : ""}
              </span>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar bg-white">
            <Show when={!templates.loading} fallback={<div class="p-4 text-xs text-center text-slate-400">Loading...</div>}>
              <For each={templates()}>
                {(item) => {
                  const isSelected = () => selectedId() === item.id;
                  return (
                    <div
                      onClick={() => setSearchParams({ template: item.id }, { replace: true })}
                      class="group flex flex-col p-2 rounded-md cursor-pointer transition-all border"
                      classList={{
                        "bg-slate-100 border-slate-300 shadow-sm": isSelected(),
                        "border-transparent hover:bg-slate-50 hover:border-slate-200": !isSelected()
                      }}
                    >
                      <div class="flex items-center justify-between gap-2">
                        <span class="font-medium text-sm truncate">{item.templateName}</span>
                        <div
                          class="size-2 rounded-full shrink-0"
                          classList={{
                            "bg-green-500": item.status === "ready",
                            "bg-amber-400": item.status === "pending"
                          }}
                        />
                      </div>
                      <span class="text-[10px] font-medium text-slate-400 uppercase tracking-widest mt-1 truncate">
                        {item.groupName}
                      </span>
                    </div>
                  );
                }}
              </For>
            </Show>
          </div>
        </div>
      </aside>

      <section class="flex-1 flex flex-col min-h-0">
        <div class="flex-1 min-h-0 flex flex-col h-full bg-white text-slate-800 font-sans select-none border border-slate-200 rounded-md overflow-hidden shadow-sm">
          <div class="p-4 space-y-4 border-b border-slate-200 bg-slate-50 shrink-0">
            <div class="flex items-center justify-between text-xs text-slate-500">
              <span class="font-medium uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
                 <FiSettings class="size-3.5" /> Configuration
              </span>
              <button class="px-3 py-1.5 rounded border border-blue-600 bg-blue-600 hover:bg-blue-700 text-white transition-colors shadow-sm text-sm font-medium flex items-center gap-1.5">
                <FiPlay class="size-3.5" /> Deploy
              </button>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-4 custom-scrollbar bg-white">
            <Show when={!templateDetails.loading && templateDetails()}>
              {(details) => (
                <>
                  <div class="flex justify-between items-center mb-6 pb-4 border-b border-slate-100">
                    <div class="flex items-center gap-3">
                      <div class="p-2 bg-blue-50 text-blue-600 rounded-md border border-blue-100">
                        <FiServer class="size-5" />
                      </div>
                      <div class="flex flex-col min-w-0">
                        <span class="font-medium text-sm text-slate-800 truncate">
                          {details().templateName}
                        </span>
                        <span class="text-[10px] font-medium text-slate-400 uppercase tracking-widest mt-0.5 truncate">
                          {details().groupName}
                        </span>
                      </div>
                    </div>
                    <A
                      href={`/workspace/${selectedId()}`}
                      class="text-[10px] uppercase font-medium px-2 py-1 rounded bg-white border border-slate-300 hover:bg-slate-100 text-slate-600 transition-colors shadow-sm flex items-center gap-1"
                    >
                      <FiEdit2 class="size-3" /> Edit
                    </A>
                  </div>

                  <div class="flex flex-col gap-4 max-w-2xl">
                    <For each={details().fields}>
                      {(field) => (
                        <div class="flex flex-col gap-1.5">
                          <label class="text-[10px] font-medium text-slate-500 uppercase tracking-widest pl-1">
                            {field.label}
                          </label>
                          <Show
                            when={field.type === "select"}
                            fallback={
                              <input type={field.type} value={field.value} class="bg-white border border-slate-300 rounded px-3 py-1.5 text-sm outline-none focus:border-blue-500 text-slate-800 placeholder-slate-400 transition-colors" disabled />
                            }
                          >
                            <select class="bg-white border border-slate-300 rounded px-3 py-1.5 text-sm outline-none focus:border-blue-500 text-slate-800 transition-colors cursor-pointer" disabled>
                              <For each={field.options}>
                                {(option) => <option selected={option === field.value} value={option}>{option}</option>}
                              </For>
                            </select>
                          </Show>
                        </div>
                      )}
                    </For>
                  </div>
                </>
              )}
            </Show>
          </div>
        </div>
      </section>
    </div>
  );
};

export default DeploySession;
