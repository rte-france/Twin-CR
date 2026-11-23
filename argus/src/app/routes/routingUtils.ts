/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

let cachedParentLabel: string | null = null;

export function resolveInitialPath(): string {
  if (typeof window === "undefined") return "/";

  const params = new URLSearchParams(window.location.search);
  const parent = params.get("parent");
  if (parent) {
    cachedParentLabel = parent;
  }

  const routeParam = params.get("route");
  if (routeParam) {
    const decoded = decodeURIComponent(routeParam);
    // Align window.location with the target route so Router matches immediately
    window.history.replaceState(null, "", decoded);
    return decoded;
  }

  return window.location.pathname || "/";
}

export function getParentLabelFromUrl(): string | null {
  if (cachedParentLabel) return cachedParentLabel;
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  return params.get("parent");
}

export function isDetachedWindow(): boolean {
  if (typeof window === "undefined") return false;

  const params = new URLSearchParams(window.location.search);
  return params.get("detached") === "true" || !!params.get("parent") || !!cachedParentLabel;
}

export function resetRoutingCache(): void {
  cachedParentLabel = null;
}
