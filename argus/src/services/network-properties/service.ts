/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { backendGet, backendPost } from "@/services/backend";
import { useAppMode } from "@/hooks/useAppMode";

/** Value of a network table cell (GET /network/component-types-rows) */
export type NetworkPropertyValue = string | number | boolean | null;

// The component type of an id and the columns of a type do not change for a given backend: cached per app mode (i.e. per backend). Failures are not cached.
const typeCache = new Map<string, Promise<string>>();
const columnsCache = new Map<string, Promise<string[]>>();

const [mode] = useAppMode();

const cached = <T>(cache: Map<string, Promise<T>>, key: string, load: () => Promise<T>): Promise<T> => {
  const k = `${mode()}|${key}`;
  let p = cache.get(k);
  if (!p) {
    p = load();
    cache.set(k, p);
    p.catch(() => cache.delete(k));
  }
  return p;
};

/** Network table (component type) of an equipment, e.g. "generator", "line"; null if unknown or unavailable */
export const typeOf = (id: string): Promise<string | null> =>
  cached(typeCache, id, () =>
    backendGet<{ type: string }>(`/network/type-of?id=${encodeURIComponent(id)}`).then((r) => r.type),
  ).catch(() => null);

/** Columns of a network table */
export const columnsOf = (type: string): Promise<string[]> =>
  cached(columnsCache, type, () =>
    backendGet<{ columns: string[] }>(`/network/component-types-schema/${type}`).then((r) => r.columns),
  );

/** Rows of a network table, by id, as {column: value} (not cached: values can be edited) */
export const rowsOf = async (
  type: string,
  ids: string[],
): Promise<Record<string, Record<string, NetworkPropertyValue>>> => {
  const [columns, rows] = await Promise.all([
    columnsOf(type),
    backendPost<Record<string, NetworkPropertyValue[]>>(`/network/component-types-rows/${type}`, ids),
  ]);
  const result: Record<string, Record<string, NetworkPropertyValue>> = {};
  for (const [id, row] of Object.entries(rows)) {
    result[id] = Object.fromEntries(columns.map((c, i) => [c, row[i] ?? null]));
  }
  return result;
};
