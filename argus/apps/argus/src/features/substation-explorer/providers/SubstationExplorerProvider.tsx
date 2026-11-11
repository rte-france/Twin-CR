/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createContext,
  createSignal,
  useContext,
  type Accessor,
  type Component,
  type JSX,
} from "solid-js";
import { useSubstationList } from "../hooks/useSubstationList";
import { openInCentral } from "@/utils/openInCentral";
import type { Type } from "../types";

interface SubstationExplorerContextValue extends ReturnType<
  typeof useSubstationList
> {
  handleOpenSld: (equipmentId: string, type: Type) => void;
  toggleExpand: (id: string) => void;
  toggleAll: () => void;
  expanded: Accessor<Set<string>>;
}

const SubstationExplorerContext =
  createContext<SubstationExplorerContextValue>();

export const useSubstationExplorerContext = () => {
  const context = useContext(SubstationExplorerContext);
  if (!context) {
    throw new Error(
      "useSubstationExplorerContext doit être utilisé dans un SubstationExplorerProvider",
    );
  }
  return context;
};

interface Props {
  children: JSX.Element;
}

export const SubstationExplorerProvider: Component<Props> = (props) => {
  const [expanded, setExpanded] = createSignal<Set<string>>(new Set<string>());

  const substationList = useSubstationList();

  const handleOpenSld = (equipmentId: string, type: Type) => {
    openInCentral({
      id: `${type} - ${equipmentId}`,
      title: `${type} - ${equipmentId}`,
      elementTag: "sld-viewer",
      params: {
        equipmentId,
        type,
      },
    });
  };

  const toggleExpand = (id: string) => {
    const next = new Set(expanded());
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpanded(next);
  };

  const toggleAll = () => {
    if (expanded().size > 0) {
      setExpanded(new Set<string>());
    } else {
      const allIds = substationList.substations().map((s) => s.id);
      setExpanded(new Set<string>(allIds));
    }
  };

  return (
    <SubstationExplorerContext.Provider
      value={{
        ...substationList,
        handleOpenSld,
        toggleExpand,
        toggleAll,
        expanded,
      }}
    >
      {props.children}
    </SubstationExplorerContext.Provider>
  );
};
