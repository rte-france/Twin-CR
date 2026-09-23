/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the TwinEU-core project.
*/

import type { ElementType } from "./ElementType";

export type SldLayoutType = "matrix" | "positioned";

export interface SldElementRef {
  id: string;
  type: ElementType;
}

export interface SldPosition {
  x: number;
  y: number;
}

export interface SldDiagramParams {
  elements: SldElementRef[];
  layoutType: SldLayoutType;
  /** Element ids laid out on a grid, "" for an empty cell. */
  matrix: string[][];
  /** Top-left corner of each element, by element id. */
  positions: Record<string, SldPosition>;
}

export interface SldDiagram {
  id: string;
  name: string;
  params: SldDiagramParams;
}

export const POSITION_STEP = 100;

export const createDefaultSldDiagram = (
  id: string,
  name: string,
): SldDiagram => ({
  id,
  name,
  params: {
    elements: [],
    layoutType: "matrix",
    matrix: [],
    positions: {},
  },
});

export const singleElementParams = (
  id: string,
  type: ElementType,
): SldDiagramParams => ({
  elements: [{ id, type }],
  layoutType: "matrix",
  matrix: [[id]],
  positions: {},
});

const matrixIds = (matrix: string[][]) =>
  matrix.flat().filter((id) => id !== "");

/**
 * Keeps the matrix and the positions in sync with the element list: ids that are no longer selected are
 * dropped, newly selected ones take the first free cell (a row is added when the grid is full) and a
 * position on a diagonal, so that a freshly added element never lands on top of another one.
 */
export const syncLayout = (params: SldDiagramParams): SldDiagramParams => {
  const ids = params.elements.map((e) => e.id);
  const columnCount = Math.max(
    1,
    ...params.matrix.map((row) => row.length),
    Math.ceil(Math.sqrt(ids.length)),
  );

  const kept = matrixIds(params.matrix).filter((id) => ids.includes(id));
  const cells = [...kept, ...ids.filter((id) => !kept.includes(id))];
  const matrix: string[][] = [];
  for (let row = 0; row * columnCount < cells.length; row++) {
    matrix.push(
      Array.from(
        { length: columnCount },
        (_, col) => cells[row * columnCount + col] ?? "",
      ),
    );
  }

  const positions: Record<string, SldPosition> = {};
  ids.forEach((id, index) => {
    positions[id] = params.positions[id] ?? {
      x: index * POSITION_STEP,
      y: 0,
    };
  });

  return { ...params, matrix, positions };
};

/** Element ids of the layout that do not place every selected element exactly once. */
export const layoutErrors = (params: SldDiagramParams): string[] => {
  if (params.elements.length < 2 || params.layoutType !== "matrix") return [];
  const placed = matrixIds(params.matrix);
  const duplicated = placed.filter((id, i) => placed.indexOf(id) !== i);
  const missing = params.elements
    .map((e) => e.id)
    .filter((id) => !placed.includes(id));
  return [...new Set([...duplicated, ...missing])];
};
