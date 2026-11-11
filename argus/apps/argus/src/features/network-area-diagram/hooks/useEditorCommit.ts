/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Console } from "effect";
import { useNadContext } from "../hooks/useNadContext";
import { useEditorContext } from "./useEditorContext";
import { NadResponse } from "../types";
import { backendGet } from "@/services/backend";

export function useEditorCommit() {
  const nadCtx = useNadContext();
  const { editorState, resetNodePositions } = useEditorContext();

  const commitToServer = () => {
    const nodes = nadCtx.nadData()?.metadata?.nodes ?? [];
    const overrides = editorState.nodePositions;

    if (Object.keys(overrides).length === 0) return;

    const textNodes: Record<
      string,
      {
        shiftX: number;
        shiftY: number;
        connectionShiftX: number;
        connectionShiftY: number;
      }
    > = Object.fromEntries(
      (nadCtx.nadData()?.metadata?.textNodes ?? []).map((tn: any) => [
        tn.svgId,
        {
          shiftX: tn.shiftX ?? 100,
          shiftY: tn.shiftY ?? -40,
          connectionShiftX: tn.connectionShiftX ?? 100,
          connectionShiftY: tn.connectionShiftY ?? -15,
        },
      ]),
    );

    const fixedPositions = nodes.map((node: any) => {
      const override = overrides[node.svgId];
      const pos = override ?? { x: node.x, y: node.y };
      const tn = textNodes[node.svgId];

      return {
        id: node.equipmentId,
        x: pos.x,
        y: pos.y,
        legend_shift_x: tn?.shiftX ?? 100,
        legend_shift_y: tn?.shiftY ?? -40,
        legend_connection_shift_x: tn?.connectionShiftX ?? 100,
        legend_connection_shift_y: tn?.connectionShiftY ?? -15,
      };
    });

    const currentIds = nadCtx.vlIds();
    const primaryId = currentIds[0] || "";
    const depth = nadCtx.depth();
    const layoutMode = nadCtx.layout();
    const radiusFactor = nadCtx.radiusFactor();

    const params = new URLSearchParams({
      voltageLevels: currentIds.join(","),
      depth: String(depth),
      fixed_positions: JSON.stringify(fixedPositions),
      layout: layoutMode,
      radiusFactor: String(radiusFactor),
    });

    const endpoint = `/nad/${encodeURIComponent(primaryId)}?${params.toString()}`;

    backendGet<NadResponse>(endpoint)
      .then(() => {
        nadCtx.setFixedPositions(fixedPositions);
        nadCtx.triggerLoad();
      })
      .catch((e) => Console.error("Failed to commit positions", e));
  };

  return { commitToServer };
}
