/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export interface HydratedPanelState {
  id: string;
  manifest: {
    id: string;
    label: string;
    iconId: string;
    elementTag: string;
    entryUrl?: string;
    isLocalFile?: boolean;
  };
  componentProps: Record<string, any>;
}

export function hydratePanelFromUrlAndStorage(
  rawId: string,
  searchParams: Record<string, string | undefined>,
  viewTypeParam?: string,
): HydratedPanelState {
  const id = decodeURIComponent(rawId);
  const storageKey = `detached_payload_${id}`;
  const storedData = typeof localStorage !== "undefined" ? localStorage.getItem(storageKey) : null;

  let parsedStorage: any = null;
  if (storedData) {
    try {
      parsedStorage = JSON.parse(storedData);
    } catch {
      parsedStorage = null;
    }
  }

  const queryViewType = searchParams.viewType || searchParams.elementTag;
  const elementTag =
    parsedStorage?.elementTag ||
    viewTypeParam ||
    queryViewType ||
    "default";

  const label =
    parsedStorage?.label ||
    parsedStorage?.title ||
    searchParams.title ||
    searchParams.label ||
    id;

  const iconId = parsedStorage?.iconId || searchParams.iconId || "file";
  const entryUrl = parsedStorage?.entryUrl || searchParams.entryUrl || undefined;
  const isLocalFile =
    parsedStorage?.isLocalFile ??
    (searchParams.isLocalFile === "true" ? true : undefined);

  let queryProps: Record<string, any> = {};
  if (searchParams.props) {
    try {
      queryProps = JSON.parse(decodeURIComponent(searchParams.props));
    } catch {
      queryProps = {};
    }
  }

  const componentProps = parsedStorage?.params || parsedStorage || queryProps;

  return {
    id,
    manifest: {
      id,
      label,
      iconId,
      elementTag,
      entryUrl,
      isLocalFile,
    },
    componentProps,
  };
}
