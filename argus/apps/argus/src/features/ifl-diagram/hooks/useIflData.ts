/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createResource, Accessor } from "solid-js";
import { IflResponse } from "../types";
import { backendGet } from "@/services/backend";

export function useIflData(
  nodes: Accessor<string[]>,
  depth: Accessor<number>,
  triggerRefetch: Accessor<number>,
) {
  const fetcher = async (): Promise<IflResponse> => {
    const params = new URLSearchParams({ depth: String(depth()) });
    if (nodes().length) params.set("nodes", nodes().join(","));
    const endpoint = `/ifl-graph?${params}`;

    try {
      const data = await backendGet<{ svg_content: string }>(endpoint);
      return { success: true, svg_content: data.svg_content };
    } catch (e) {
      return { success: false, error: `Failed to fetch IFL graph: ${e}` };
    }
  };

  return createResource(
    () => `${nodes().join(",")}-${depth()}-${triggerRefetch()}`,
    fetcher,
  );
}
