/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import * as d3 from "d3";
import { Accessor, onCleanup } from "solid-js";

declare module "solid-js" {
  namespace JSX {
    interface Directives {
      d3Zoom: {
        onZoom: (t: d3.ZoomTransform) => void;
        onRightClick: (e: MouseEvent) => void;
        registerFit: (fitFn: () => void) => void;
      };
    }
  }
}

export function d3Zoom(el: HTMLDivElement, accessor: Accessor<any>) {
  const config = accessor();

  const zoomBeh = d3
    .zoom<HTMLDivElement, unknown>()
    .scaleExtent([0.05, 50])
    .on("zoom", (ev) => config.onZoom(ev.transform));

  d3.select(el).call(zoomBeh);

  const handleContext = (e: MouseEvent) => {
    e.preventDefault();
    config.onRightClick(e);
  };
  el.addEventListener("contextmenu", handleContext);

  config.registerFit(
    (xEx: [number, number], yEx: [number, number], cw: number, ch: number) => {
      const k =
        Math.min(
          cw / Math.max(xEx[1] - xEx[0], 1),
          ch / Math.max(yEx[1] - yEx[0], 1),
        ) * 0.8;
      const tx = cw / 2 - ((xEx[0] + xEx[1]) / 2) * k;
      const ty = ch / 2 - ((yEx[0] + yEx[1]) / 2) * k;
      d3.select(el)
        .transition()
        .duration(500)
        .call(zoomBeh.transform, d3.zoomIdentity.translate(tx, ty).scale(k));
    },
  );

  onCleanup(() => {
    el.removeEventListener("contextmenu", handleContext);
  });
}
