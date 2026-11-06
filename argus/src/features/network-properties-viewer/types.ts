/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface CustomColumn {
  name: string;
  expression: string;  // JS expression using column names as variables
}

export interface ComponentTypeConfig {
  visibleColumns: string[] | null;  // null = all columns visible
  customColumns: CustomColumn[];
}

export const defaultComponentTypeConfig = (): ComponentTypeConfig => ({
  visibleColumns: null,
  customColumns: [],
});

export interface NetworkPropertiesPanel {
  id: string;
  name: string;
  params: {
    componentType: string;
    config: ComponentTypeConfig;
  };
}

export interface ElementSchemaResponse {
  columns: string[];
  ids: string[];
}

export type ElementRowsResponse = Record<string, (string | number | boolean | null)[]>;

export interface PendingEdit {
  rowId: string;
  column: string;
  originalValue: unknown;
  newValue: unknown;
}

// Map of equipmentId -> list of controllable columns
export type ControllabilityMap = Record<string, string[]>;

type DynamicSource = "mapping" | "estim";

export interface DynamicKind {
  kind: string;
  side: string | null;
  source: DynamicSource;
  field: string; // `__dynamic_mapping__${kind}` or `__dynamic_estim__${kind}`
}
