/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, onCleanup, createSignal, type Accessor } from "solid-js";
import type { Metadata } from "../types/Metadata";

export type SelectedActionItem = | { equipmentId: string; side: string | null } | null;

interface UseActionPanelProps {
  svgRef: Accessor<SVGSVGElement | undefined>;
  metadata: Accessor<Metadata | undefined>;
}

export const useActionPanelSelection = (props: UseActionPanelProps) => {
  const [selectedItem, setSelectedItem] = createSignal<SelectedActionItem>(null);

  createEffect(() => {
    const svg = props.svgRef();
    const meta = props.metadata();

    if (!svg || !meta) return;

    const nodeMap = new Map(meta.nodes.map((n) => [n.id, n]));
    const feederMap = new Map(meta.feederInfos.map((f) => [f.id, f]));

    const handleContextMenu = (e: MouseEvent) => {
      let current = e.target as SVGElement | null;
      let matchedItem: SelectedActionItem = null;

      while (current && current !== svg) {
        if (current.id) {
          if (nodeMap.has(current.id)) {
            const equipmentId = nodeMap.get(current.id)!.equipmentId;
            if (equipmentId) {
              matchedItem = {
                equipmentId: equipmentId,
                side: null,
              };
              break;
            }
          }
          if (feederMap.has(current.id)) {
            matchedItem = {
              equipmentId: feederMap.get(current.id)!.equipmentId,
              side: feederMap.get(current.id)!.side ?? null,
            };
            break;
          }
        }
        current = current.parentElement as SVGElement | null;
      }

      if (matchedItem) {
        e.preventDefault();
        setSelectedItem(matchedItem);
      } else {
        setSelectedItem(null);
      }
    };

    const handleCloseClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;

      if (target?.closest("[data-action-panel]")) {
        return;
      }

      if (selectedItem()) {
        setSelectedItem(null);
      }
    };

    svg.addEventListener("contextmenu", handleContextMenu);
    document.addEventListener("click", handleCloseClick);

    onCleanup(() => {
      svg.removeEventListener("contextmenu", handleContextMenu);
      document.removeEventListener("click", handleCloseClick);
    });
  });

  return { selectedItem, setSelectedItem };
};
