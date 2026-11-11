/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, onCleanup, type Accessor } from "solid-js";
import type { Metadata } from "../types/Metadata";

interface LineGoToProps {
  svgRef: Accessor<SVGSVGElement | undefined>;
  metadata: Accessor<Metadata | undefined>;
  onGoToVoltageLevel?: (nextVId: string) => void;
}

export const useLineGoTo = (props: LineGoToProps) => {
  createEffect(() => {
    const svgElement = props.svgRef();
    const metadata = props.metadata();

    if (!svgElement || !metadata) return;

    const lineNodes = metadata.nodes.filter((node) => node.nextVId);

    let styleEl = document.getElementById("sld-line-goto-styles");
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = "sld-line-goto-styles";
      document.head.appendChild(styleEl);
    }

    if (lineNodes.length > 0) {
      const baseSelectors = lineNodes
        .map((n) => `#${CSS.escape(n.id)} text.sld-label[id$="_95_LABEL"]`)
        .join(", ");
      const hoverSelectors = lineNodes
        .map((n) => `#${CSS.escape(n.id)} text.sld-label[id$="_95_LABEL"]:hover`)
        .join(", ");

      styleEl.innerHTML = `
        ${baseSelectors} {
          cursor: pointer !important;
          transition: all 0.2s ease;
        }
        ${hoverSelectors} {
          text-decoration: underline !important;
          opacity: 0.7 !important;
        }
      `;
    } else {
      styleEl.innerHTML = "";
    }

    const handleLabelClick = (event: MouseEvent) => {
      const target = event.target as SVGElement;
      const callback = props.onGoToVoltageLevel;

      if (
        !callback ||
        target.tagName.toLowerCase() !== "text" ||
        !target.classList.contains("sld-label") ||
        !target.id.endsWith("_95_LABEL")
      ) {
        return;
      }

      const parentGroup = target.closest("g[id]");
      if (!parentGroup) return;

      const lineNode = lineNodes.find((node) => node.id === parentGroup.id);

      if (lineNode?.nextVId) {
        event.preventDefault();
        event.stopPropagation();
        callback(lineNode.nextVId);
      }
    };

    svgElement.addEventListener("click", handleLabelClick);

    onCleanup(() => {
      svgElement.removeEventListener("click", handleLabelClick);
    });
  });
};
