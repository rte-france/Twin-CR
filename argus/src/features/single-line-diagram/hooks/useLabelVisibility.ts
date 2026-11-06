/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createEffect, type Accessor } from "solid-js";
import type { Metadata } from "../types/Metadata";

interface UseLabelVisibilityProps {
  svgRef: Accessor<SVGSVGElement | undefined>;
  metadata: Accessor<Metadata | undefined>;
  showProtectionLabels: Accessor<boolean>;
  showMeasurementLabels: Accessor<boolean>;
}

export const useLabelVisibility = (props: UseLabelVisibilityProps) => {
  createEffect(() => {
    const svg = props.svgRef();
    const meta = props.metadata();
    const showProtection = props.showProtectionLabels();
    const showMeasurement = props.showMeasurementLabels();

    if (!svg || !meta) return;

    svg
      .querySelectorAll<SVGTextElement>('text.sld-label[id*="_95_PE_95_"]')
      .forEach((el) => {
        el.style.display = showProtection ? "" : "none";
      });

    svg
      .querySelectorAll<SVGTextElement>("g.sld-feeder-info text.sld-label")
      .forEach((el) => {
        if (!el.textContent?.startsWith("M:")) return;
        const group = el.closest<SVGGElement>("g.sld-feeder-info");
        if (group) group.style.display = showMeasurement ? "" : "none";
      });
  });
};
