/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, onCleanup, createSignal, type Accessor } from "solid-js";
import type { Metadata } from "../types/Metadata";

export interface ProtectionEquipmentMetadata {
  libelle?: string;
  tase2?: string;
  tase2_control?: string | null;
  value?: string;
  [key: string]: unknown;
}

export interface SelectedProtectionEquipment {
  label: string;
  metadata: ProtectionEquipmentMetadata;
}

interface UseProtectionEquipmentLabelsProps {
  svgRef: Accessor<SVGSVGElement | undefined>;
  metadata: Accessor<Metadata | undefined>;
}

// Powsybl-sld escapes every character that is not [A-Za-z0-9-] in a raw
// label/node id as `_<charCode>_`, then prefixes the result with "id" to
// build the actual SVG element id (e.g. "VL1 BAY1_ONE_PE_black_0" becomes
// "idVL1_32_BAY1_95_ONE_95_PE_95_black_95_0").
const escapeSvgId = (raw: string): string =>
  "id" +
  Array.from(raw)
    .map((c) => (/[A-Za-z0-9-]/.test(c) ? c : `_${c.charCodeAt(0)}_`))
    .join("");

export const useProtectionEquipmentLabels = (
  props: UseProtectionEquipmentLabelsProps,
) => {
  const [selected, setSelected] =
    createSignal<SelectedProtectionEquipment | null>(null);

  createEffect(() => {
    const svg = props.svgRef();
    const meta = props.metadata();

    if (!svg || !meta) return;

    const metadataById = new Map<string, ProtectionEquipmentMetadata>();
    for (const node of meta.nodes) {
      for (const label of node.labels ?? []) {
        if (
          // Protection equipment labels start with "PE_" and always have metadata (userDefinedId (containing a json string) in powsybl)
          !label.positionName.startsWith("PE_") ||
          !label.userDefinedId
        ) {
          continue;
        }
        try {
          metadataById.set(
            escapeSvgId(label.id),
            JSON.parse(label.userDefinedId),
          );
        } catch (e) {
          console.warn(`[PE labels] Failed to parse metadata for ${label.id}`, e);
        }
      }
    }

    const styleId = "sld-pe-label-styles";
    let styleEl = document.getElementById(styleId);
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = styleId;
      document.head.appendChild(styleEl);
    }
    styleEl.innerHTML =
      metadataById.size > 0
        ? `text.sld-label[id*="_95_PE_95_"] { cursor: pointer; }
           text.sld-label[id*="_95_PE_95_"]:hover { text-decoration: underline; }`
        : "";

    const handleClick = (e: MouseEvent) => {
      let current = e.target as SVGElement | null;

      while (current && current !== svg) {
        if (current.id && metadataById.has(current.id)) {
          e.preventDefault();
          e.stopPropagation();
          setSelected({
            label: current.textContent ?? "",
            metadata: metadataById.get(current.id)!,
          });
          return;
        }
        current = current.parentElement as SVGElement | null;
      }
    };

    svg.addEventListener("click", handleClick);

    onCleanup(() => {
      svg.removeEventListener("click", handleClick);
    });
  });

  return { selected, setSelected };
};
