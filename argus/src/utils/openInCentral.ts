/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export const ADD_CENTRAL_EVENT = "argus:add-central";

export interface OpenCentralParams {
  id: string;
  title: string;
  elementTag: string;
  params?: Record<string, any>;
  entryUrl?: string;
  isLocalFile?: boolean;
}

export const openInCentral = (payload: OpenCentralParams) => {
  window.dispatchEvent(new CustomEvent(ADD_CENTRAL_EVENT, { detail: payload }));
};
