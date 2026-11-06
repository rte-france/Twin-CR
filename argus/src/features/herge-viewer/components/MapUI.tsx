/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { type Component } from "solid-js";

export const MapLoadingOverlay: Component<{ show: boolean }> = (props) =>
  props.show ? (
    <div class="absolute top-3 right-14 bg-bg/80 border border-border rounded-lg py-2 px-3 z-600 flex items-center gap-2 text-[11px] text-icons backdrop-blur-sm shadow-sm">
      <span class="w-3.5 h-3.5 border-2 border-border border-t-links rounded-full animate-spin shrink-0" />
      Chargement carte...
    </div>
  ) : null;

export const MapEmptyState: Component<{ show: boolean }> = (props) =>
  props.show ? (
    <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 pointer-events-none z-500">
      <svg
        width="56"
        height="56"
        viewBox="0 0 56 56"
        fill="none"
        class="opacity-40 text-icons"
      >
        <rect
          x="6"
          y="14"
          width="44"
          height="32"
          rx="3"
          stroke="currentColor"
          stroke-width="1.8"
        />
        <path
          d="M6 24 Q18 18 28 24 Q38 30 50 24"
          stroke="currentColor"
          stroke-width="1.4"
          fill="none"
        />
        <path
          d="M6 36 Q20 30 36 36 Q46 40 50 36"
          stroke="currentColor"
          stroke-width="1.4"
          fill="none"
        />
      </svg>
      <p class="text-xs text-icons m-0">
        Activez des couches pour afficher la carte
      </p>
    </div>
  ) : null;

export const MapScaleBar: Component<{ widthPx: number; label: string }> = (
  props,
) => (
  <div class="absolute bottom-10 left-3.5 flex flex-col gap-0.75 pointer-events-none z-500">
    <div
      class="h-1 bg-icons rounded-[1px] border-x-2 border-icons min-w-5 max-w-37.5 transition-[width] duration-300"
      style={{ width: `${props.widthPx}px` }}
    />
    <span class="text-[9px] text-icons font-bold">{props.label}</span>
  </div>
);

export const MapCoordsBar: Component<{
  x: number;
  y: number;
  ratio: number;
}> = (props) => (
  <div class="absolute bottom-2.5 left-1/2 -translate-x-1/2 flex items-center gap-2 px-3.5 py-1 bg-bg/85 border border-border rounded-full text-[10px] text-icons pointer-events-none whitespace-nowrap backdrop-blur-md z-500 shadow-sm">
    <span class="font-mono">X {props.x.toLocaleString("fr-FR")}</span>
    <span class="text-border">•</span>
    <span class="font-mono">Y {props.y.toLocaleString("fr-FR")}</span>
    <span class="text-border">•</span>
    <span class="font-mono">1:{props.ratio.toLocaleString("fr-FR")}</span>
  </div>
);
