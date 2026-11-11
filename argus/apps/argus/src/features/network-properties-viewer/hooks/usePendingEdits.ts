/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { PendingEdit } from "../types";

export function usePendingEdits() {
  const [pendingEdits, setPendingEdits] = createSignal<PendingEdit[]>([]);
  const [committedEdits, setCommittedEdits] = createSignal<PendingEdit[]>([]);

  const addEdit = (edit: PendingEdit) => {
    setPendingEdits((prev) => {
      const existing = prev.find(
        (e) => e.rowId === edit.rowId && e.column === edit.column
      );
      const originalValue = existing ? existing.originalValue : edit.originalValue;
      const filtered = prev.filter(  // Clear any existing edit for same row/column
        (e) => !(e.rowId === edit.rowId && e.column === edit.column)
      );
      return [...filtered, { ...edit, originalValue }];
    });
  };

  const removeEdit = (rowId: string, column: string) => {
    setPendingEdits((prev) => prev.filter((e) => !(e.rowId === rowId && e.column === column)));
  };

  const commitEdit = (rowId: string, column: string) => {
    const edit = pendingEdits().find((e) => e.rowId === rowId && e.column === column);
    if (edit) {
      setCommittedEdits((prev) => [...prev.filter((e) => !(e.rowId === rowId && e.column === column)), edit]);
      removeEdit(rowId, column);
    }
  };

  const clearEdits = () => setPendingEdits([]);

  const hasEdits = () => pendingEdits().length > 0;

  return { pendingEdits, committedEdits, addEdit, clearEdits, hasEdits, commitEdit };
}
