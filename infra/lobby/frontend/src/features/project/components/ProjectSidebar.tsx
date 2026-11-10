/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { createResource, createSignal, For, Show } from "solid-js";
import { Effect, Context } from "effect";
import { ProjectService } from "@/features/project/services";
import { getSystemRuntime } from "@/utils/getSystemRuntime";

const runProject = <A, E>(f: (svc: Context.Tag.Service<typeof ProjectService>) => Effect.Effect<A, E>) =>
  getSystemRuntime().runPromise(ProjectService.pipe(Effect.andThen(f)));

export function ProjectSidebar(props: {
  onSelectProject: (projectId: string) => void;
  selectedProjectId?: string | null;
}) {
  const [groups, { refetch: refetchGroups }] = createResource(() =>
    runProject((svc) => svc.fetchGroups)
  );

  const [projects, { refetch: refetchProjects }] = createResource(() =>
    runProject((svc) => svc.fetchProjects)
  );

  const [newGroupName, setNewGroupName] = createSignal("");
  const [newProjectNames, setNewProjectNames] = createSignal<Record<string, string>>({});

  const handleCreateGroup = async (e: Event) => {
    e.preventDefault();
    if (!newGroupName()) return;
    await runProject((svc) => svc.createGroup(newGroupName()));
    setNewGroupName("");
    refetchGroups();
  };

  const handleCreateProject = async (groupId: string) => {
    const name = newProjectNames()[groupId];
    if (!name) return;
    await runProject((svc) => svc.createProject(name, groupId));
    setNewProjectNames((prev) => ({ ...prev, [groupId]: "" }));
    refetchProjects();
  };

  return (
    <div class="w-64 bg-gray-50 border-r border-gray-200 p-4 h-full flex flex-col gap-4 overflow-y-auto">
      <h2 class="text-lg font-semibold">Workspace Explorer</h2>

      <form onSubmit={handleCreateGroup} class="flex gap-2">
        <input
          type="text"
          placeholder="New Group"
          class="border px-2 py-1 rounded w-full text-sm"
          value={newGroupName()}
          onInput={(e) => setNewGroupName(e.currentTarget.value)}
        />
        <button type="submit" class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700">
          +
        </button>
      </form>

      <Show when={!groups.loading} fallback={<div class="text-sm text-gray-500">Loading...</div>}>
        <div class="flex flex-col gap-4">
          <For each={groups()}>
            {(group) => (
              <div class="flex flex-col gap-2">
                <div class="font-semibold text-gray-800">{group.name}</div>
                
                <ul class="flex flex-col gap-1 pl-4">
                  <For each={projects()?.filter((p) => p.group_id === group.id)}>
                    {(project) => (
                      <li>
                        <button
                          class={`text-sm w-full text-left px-2 py-1 rounded hover:bg-gray-200 ${
                            props.selectedProjectId === project.id ? "bg-gray-200 font-medium" : "text-gray-600"
                          }`}
                          onClick={() => props.onSelectProject(project.id)}
                        >
                          {project.name}
                        </button>
                      </li>
                    )}
                  </For>
                </ul>

                <div class="flex gap-2 pl-4">
                  <input
                    type="text"
                    placeholder="New Project"
                    class="border px-2 py-1 rounded w-full text-xs"
                    value={newProjectNames()[group.id] || ""}
                    onInput={(e) =>
                      setNewProjectNames((prev) => ({ ...prev, [group.id]: e.currentTarget.value }))
                    }
                  />
                  <button
                    onClick={() => handleCreateProject(group.id)}
                    class="bg-green-600 text-white px-2 py-1 rounded text-xs hover:bg-green-700"
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
          </For>
        </div>
      </Show>
    </div>
  );
}
