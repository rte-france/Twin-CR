/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createContext,
  useContext,
  createEffect,
  type ParentComponent,
} from "solid-js";
import { createStore } from "solid-js/store";

export type PanelSide = "left" | "right" | "bottom" | "central";

interface SideState {
  activeId: string;
  size: number;
  isVisible: boolean;
}

interface LayoutState {
  left: SideState;
  right: SideState;
  bottom: SideState;
  central: SideState;
}

const DEFAULT_STATE: LayoutState = {
  left: { activeId: "equipment-explorer", size: 280, isVisible: true },
  right: { activeId: "", size: 280, isVisible: false },
  bottom: { activeId: "", size: 250, isVisible: false },
  central: { activeId: "", size: 100, isVisible: true },
};

interface LayoutContextType {
  state: LayoutState;
  togglePanel: (side: PanelSide, id: string) => void;
  toggle: (side: PanelSide) => void;
  setActiveId: (side: PanelSide, id: string | null) => void;
  setDim: (side: PanelSide, size: number) => void;
  isOpen: (side: PanelSide, id?: string) => boolean;
}

const LayoutContext = createContext<LayoutContextType>();

// 1. AJOUT: On définit les props attendues par le Provider
interface LayoutProviderProps {
  windowLabel: string;
}

// 2. MODIFICATION: On type le composant pour accepter windowLabel
export const LayoutProvider: ParentComponent<LayoutProviderProps> = (props) => {
  // 3. AJOUT: On crée la clé de stockage unique pour cette fenêtre
  const storageKey = `argus-layout-state-${props.windowLabel}`;

  const getInitialState = (): LayoutState => {
    try {
      // 4. MODIFICATION: On lit depuis la clé unique
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        return { ...DEFAULT_STATE, ...parsed };
      }
      return DEFAULT_STATE;
    } catch {
      return DEFAULT_STATE;
    }
  };

  const [state, setState] = createStore<LayoutState>(getInitialState());

  createEffect(() => {
    // 5. MODIFICATION: On sauvegarde dans la clé unique
    localStorage.setItem(storageKey, JSON.stringify(state));
  });

  const togglePanel = (side: PanelSide, id: string) => {
    const currentSide = state[side];
    if (currentSide.activeId === id) {
      setState(side, "isVisible", !currentSide.isVisible);
    } else {
      setState(side, {
        activeId: id,
        isVisible: true,
      });
    }
  };

  const toggle = (side: PanelSide) => {
    setState(side, "isVisible", !state[side].isVisible);
  };

  const setActiveId = (side: PanelSide, id: string | null) => {
    if (!id) {
      setState(side, "isVisible", false);
    } else {
      setState(side, { activeId: id, isVisible: true });
    }
  };

  const setDim = (side: PanelSide, size: number) => {
    setState(side, "size", size);
  };

  const isOpen = (side: PanelSide, id?: string) => {
    if (id) {
      return state[side].activeId === id && state[side].isVisible;
    }
    return state[side].isVisible;
  };

  return (
    <LayoutContext.Provider
      value={{ state, togglePanel, toggle, setActiveId, setDim, isOpen }}
    >
      {props.children}
    </LayoutContext.Provider>
  );
};

export const useLayout = () => {
  const context = useContext(LayoutContext);
  if (!context) throw new Error("useLayout must be used within LayoutProvider");
  return context;
};
