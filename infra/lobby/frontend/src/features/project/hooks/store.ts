/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { Context, Effect } from "effect";
import { createSignal } from "solid-js";
import { ProjectService } from "@/features/project/services";
import { getSystemRuntime } from "@/utils/getSystemRuntime";

export type Group = { id: string; name: string; parent_id: string | null };
export type Project = { id: string; name: string; group_id: string };

export function createProjectStore() {
  function run<A, E>(effect: Effect.Effect<A, E, ProjectService>): Promise<A> {
    return getSystemRuntime().runPromise(effect);
  }

  function runProject<A, E>(
    f: (svc: Context.Tag.Service<typeof ProjectService>) => Effect.Effect<A, E>,
  ): Promise<A> {
    return run(ProjectService.pipe(Effect.andThen(f)));
  }

  const errorMessage = (e: unknown) =>
    e instanceof Error || (typeof e === "object" && e && "message" in e)
      ? String((e as { message: unknown }).message)
      : String(e);

  const [loading, setLoading] = createSignal(false);
  const [groups, setGroups] = createSignal<Group[]>([]);
  const [projects, setProjects] = createSignal<Project[]>([]);
  const [selectedGroupId, setSelectedGroupId] = createSignal<string | null>(
    null,
  );

  // Pour gérer les dossiers ouverts/fermés dans l'arbre
  const [expandedGroups, setExpandedGroups] = createSignal<Set<string>>(
    new Set(),
  );

  const toggleGroupExpand = (id: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filteredProjects = () => {
    const gid = selectedGroupId();
    if (!gid) return projects();
    return projects().filter((p) => p.group_id === gid);
  };

  async function loadAll() {
    setLoading(true);
    try {
      const [g, p] = await Promise.all([
        runProject((svc) => svc.fetchGroups),
        runProject((svc) => svc.fetchProjects),
      ]);
      setGroups(g as Group[]);
      setProjects(p as Project[]);

      if (!selectedGroupId() && g.length > 0) {
        const rootGroups = (g as Group[]).filter(
          (group) => group.parent_id === null,
        );
        const firstGroup = rootGroups.length > 0 ? rootGroups[0] : g[0];
        if (firstGroup) setSelectedGroupId(firstGroup.id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function createGroup(name: string, parentId: string | null = null) {
    setLoading(true);
    try {
      await runProject((svc) => svc.createGroup(name, parentId));
      if (parentId) {
        // Auto-expand le parent si on crée un sous-dossier
        setExpandedGroups((prev) => new Set(prev).add(parentId));
      }
      await loadAll();
    } catch (e) {
      alert(`Error: ${errorMessage(e)}`);
    } finally {
      setLoading(false);
    }
  }

  async function deleteGroup(id: string) {
    if (!confirm("Delete group and all its contents?")) return;
    setLoading(true);
    try {
      await runProject((svc) => svc.deleteGroup(id));
      if (selectedGroupId() === id) setSelectedGroupId(null);
      await loadAll();
    } catch (e) {
      alert(`Error: ${errorMessage(e)}`);
    } finally {
      setLoading(false);
    }
  }

  async function createProject(name: string, groupId: string) {
    setLoading(true);
    try {
      await runProject((svc) => svc.createProject(name, groupId));
      await loadAll();
    } catch (e) {
      alert(`Error: ${errorMessage(e)}`);
    } finally {
      setLoading(false);
    }
  }

  async function updateProject(
    id: string,
    name: string | null,
    groupId: string | null,
  ) {
    setLoading(true);
    try {
      await runProject((svc) => svc.updateProject(id, name, groupId));
      await loadAll();
    } catch (e) {
      alert(`Error: ${errorMessage(e)}`);
    } finally {
      setLoading(false);
    }
  }

  async function deleteProject(id: string) {
    if (!confirm("Delete project?")) return;
    setLoading(true);
    try {
      await runProject((svc) => svc.deleteProject(id));
      await loadAll();
    } catch (e) {
      alert(`Error: ${errorMessage(e)}`);
    } finally {
      setLoading(false);
    }
  }

  async function duplicateProject(projectId: string, targetGroupId: string) {
    setLoading(true);
    try {
      await runProject((svc) => svc.duplicateProject(projectId, targetGroupId));
      // Auto-expand le dossier cible pour voir la copie
      setExpandedGroups((prev) => new Set(prev).add(targetGroupId));
      // Optionnel : Basculer sur le dossier cible
      // setSelectedGroupId(targetGroupId);
      await loadAll();
    } catch (e) {
      alert(`Error: ${errorMessage(e)}`);
    } finally {
      setLoading(false);
    }
  }

  async function shareGroup(
    groupId: string,
    targetUserId: string,
    role: string = "viewer",
  ) {
    setLoading(true);
    try {
      await runProject((svc) => svc.shareGroup(groupId, targetUserId, role));
      alert("Workspace shared successfully!");
    } catch (e) {
      alert(`Error: ${errorMessage(e)}`);
    } finally {
      setLoading(false);
    }
  }

  return {
    loading,
    groups,
    projects,
    filteredProjects,
    selectedGroupId,
    setSelectedGroupId,
    expandedGroups,
    toggleGroupExpand,
    loadAll,
    createGroup,
    deleteGroup,
    createProject,
    updateProject,
    deleteProject,
    duplicateProject,
    shareGroup,
  };
}
