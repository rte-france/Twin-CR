/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, onCleanup, createSignal, type Accessor } from "solid-js";
import type { Metadata } from "../types/Metadata";
import {
  EQUIPMENT_CONTROL_CLASSES,
  EQUIPMENT_CONTROL_TYPES,
} from "../types/EquipmentControl";
import { backendPost } from "@/services/backend";

interface UseEquipmentControlProps {
  svgRef: Accessor<SVGSVGElement | undefined>;
  metadata: Accessor<Metadata | undefined>;
  requester: string;
  onSuccess?: (id: string, state: string) => void;
}

const injectVisualStyles = () => {
  const styleId = "sld-equipment-control-styles";
  if (!document.getElementById(styleId)) {
    const style = document.createElement("style");
    style.id = styleId;

    const selectors = EQUIPMENT_CONTROL_CLASSES.join(", ");
    const hoverSelectors = EQUIPMENT_CONTROL_CLASSES.map(
      (c) => `${c}:hover`,
    ).join(", ");

    style.innerHTML = `
      ${selectors} {
        cursor: pointer !important;
        transition: opacity 0.15s ease-in-out;
      }
      ${hoverSelectors} {
        opacity: 0.6 !important;
      }
    `;
    document.head.appendChild(style);
  }
};

export const useEquipmentControl = (props: UseEquipmentControlProps) => {
  const [pendingIds, setPendingIds] = createSignal<Set<string>>(new Set());

  createEffect(() => {
    const ids = pendingIds();
    let styleEl = document.getElementById("dynamic-blink-style");

    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "dynamic-blink-style";
      document.head.appendChild(styleEl);
    }

    if (ids.size === 0) {
      styleEl.innerHTML = "";
    } else {
      const selectors = Array.from(ids)
        .map((id) => `#${CSS.escape(id)}`)
        .join(", ");

      styleEl.innerHTML = `
        ${selectors} {
          /* Force l'annulation des transitions pour laisser jouer l'animation */
          transition: none !important;
          animation: eq-blink 0.25s infinite alternate ease-in-out !important;
          pointer-events: none !important;
        }
        @keyframes eq-blink {
          0% { opacity: 1; filter: brightness(1); }
          100% { opacity: 0.3; filter: brightness(1.5); }
        }
      `;
    }
  });

  createEffect(() => {
    const svg = props.svgRef();
    const meta = props.metadata();

    if (!svg || !meta) return;

    injectVisualStyles();

    const nodeMap = new Map(meta.nodes.map((n) => [n.id, n]));

    const handleSvgClick = (e: MouseEvent) => {
      let current = e.target as SVGElement | null;
      let matchedNode = null;
      let matchedId = null;
      let matchedElement: SVGElement | null = null;

      while (current && current !== svg) {
        if (current.id && nodeMap.has(current.id)) {
          const node = nodeMap.get(current.id);
          if (
            node &&
            node.componentType &&
            EQUIPMENT_CONTROL_TYPES.includes(node.componentType)
          ) {
            matchedNode = node;
            matchedId = current.id;
            matchedElement = current;
            break;
          }
        }
        current = current.parentElement as SVGElement | null;
      }

      if (!matchedNode || !matchedId || !matchedNode.equipmentId) {
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      setPendingIds((prev) => new Set(prev).add(matchedId as string));

      const handleControl = async () => {
        const requester = props.requester || "operatorC";
        const safeEqId = encodeURIComponent(matchedNode.equipmentId as string);

        try {
          const status = await backendPost<Record<string, string[]>>("/control-batch-check", {
            equipmentIds: [matchedNode.equipmentId],
            columns: ["state"],
          });
          const controllable = (status[matchedNode.equipmentId as string] ?? []).includes("state");

          if (!controllable) {
            console.warn(`[EqControl] Equipment ${matchedNode.equipmentId} is not controllable.`);
            return;
          }

          // A ground disconnection is an INTERNAL node, and powsybl only writes `open` in the
          // metadata for SWITCH nodes, so its state is read from the rendered class instead.
          const currentState =
            matchedNode.componentType === "GROUND_DISCONNECTION"
              ? (matchedElement?.classList.contains("sld-open") ?? false)
              : (matchedNode.open ?? false);
          const newState = !currentState;
          const commandEndpoint = `/control/${safeEqId}/state/${String(newState)}?requester=${requester}`;

          await Promise.all([
            backendPost(commandEndpoint, {}),
            new Promise((resolve) => setTimeout(resolve, 1000)),  // Fake delay to match refresh rate
          ]);

          const strState = newState ? "opened" : "closed";
          if (props.onSuccess) props.onSuccess(matchedNode.equipmentId || matchedId, strState);
        } catch (err) {
          console.error(`[EqControl] Error for ${matchedNode?.equipmentId}:`, err);
        } finally {
          setPendingIds((prev) => {
            const next = new Set(prev);
            if (matchedId) next.delete(matchedId);
            return next;
          });
        }
      };

      handleControl();
    };

    svg.addEventListener("click", handleSvgClick);

    onCleanup(() => {
      svg.removeEventListener("click", handleSvgClick);
    });
  });

  return { pendingIds };
};
