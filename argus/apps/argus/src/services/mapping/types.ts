/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface MappingItem {
  equipmentId: string;
  kind: string;
  voltage_level: string;
  substation: string;
  topic: string;
  id: string;
  factor: number;
  side: string | null;
}

export interface MappingState {
  readonly data: MappingItem[];
  readonly isLoading: boolean;
  readonly error: Error | null;
  readonly activeMode: string | null;
}

export interface EstimVariable {
  readonly equipmentId: string;
  readonly kind: string;
  readonly topic: string;
  readonly side: string | null;
}

export interface EstimState {
  readonly data: EstimVariable[];
  readonly isLoading: boolean;
  readonly error: Error | null;
  readonly activeMode: string | null;
}
