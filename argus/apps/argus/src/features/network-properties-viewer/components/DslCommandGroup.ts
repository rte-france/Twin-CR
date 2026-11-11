/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { DslCommand } from "./dslUtils";

export interface CommandGroup {
  id: string;
  name: string;
  commands: DslCommand[];
}

export function createInitialGroups(commands: DslCommand[]): CommandGroup[] {
  return [{ id: "group-1", name: "Group 1", commands }];
}

export function moveCommandsToNewGroup(
  groups: CommandGroup[],
  commandIds: Set<string>,
): CommandGroup[] {
  const newGroupId = `group-${Date.now()}`;
  const newGroupName = `Group ${groups.length + 1}`;
  // Preserve order by collecting from flattened list
  const moved = groups
    .flatMap((g) => g.commands)
    .filter((c) => commandIds.has(c.id));

  const updatedGroups = groups
    .map((g) => ({ ...g, commands: g.commands.filter((c) => !commandIds.has(c.id)) }))
    .filter((g) => g.commands.length > 0);

  return [...updatedGroups, { id: newGroupId, name: newGroupName, commands: moved }];
}

export function moveCommandsToExistingGroup(
  groups: CommandGroup[],
  commandIds: Set<string>,
  targetGroupId: string,
): CommandGroup[] {
  const moved = groups
    .flatMap((g) => g.commands)
    .filter((c) => commandIds.has(c.id));

  return groups
    .map((g) => ({
      ...g,
      commands: g.id === targetGroupId
        ? [...g.commands, ...moved.filter((c) => !g.commands.some((e) => e.id === c.id))]
        : g.commands.filter((c) => !commandIds.has(c.id)),
    }))
    .filter((g) => g.commands.length > 0);
}
