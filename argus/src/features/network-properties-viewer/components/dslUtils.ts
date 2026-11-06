/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { PendingEdit } from "../types";
import { Effect, Exit, Cause } from "effect";
import { DslClient } from "@/services/dsl";
import { systemRuntime } from "@/config/runtime";
import { toDslKind } from "../columnMapping";

export interface DslCommand {
  id: string;
  rowId: string;
  column: string;
  componentType: string;
  dslText: string;
  originalEdit: PendingEdit;  // Edit that led the to creation of the DSL command
}

export function generateDslCommand(
  edit: PendingEdit,
  componentType: string,
): string {
  const { rowId, column, newValue } = edit;
  if (column === "open") {
    const verb = newValue === true || newValue === "true" ? "open" : "close";
    // componentType e.g. "switch"
    return `${verb} ${componentType} "${rowId}";`;
  }
  return `set ${componentType} "${rowId}" to ${newValue} ${toDslKind(column)};`;
}

export function editsToCommands(
  edits: PendingEdit[],
  componentType: string,
): DslCommand[] {
  return edits.map((edit) => ({
    id: `${edit.rowId}__${edit.column}__${Date.now()}`,
    rowId: edit.rowId,
    column: edit.column,
    componentType,
    dslText: generateDslCommand(edit, componentType),
    originalEdit: edit,
  }));
}

export function sendDslCommand(dslText: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const program = Effect.gen(function* () {
      const client = yield* DslClient;
      return yield* client.post(
        "/trainer/dsl_command",
        dslText,
        "argus:network-properties-viewer",  // TODO: put user name as source instead
      );
    });
    systemRuntime.runCallback(program, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit)) resolve();
        else reject(new Error(Cause.pretty(exit.cause)));
      },
    });
  });
}
