/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createContext,
  useContext,
  type JSX,
  type Accessor,
} from "solid-js";

interface HeaderContextValue {
  isOpen: Accessor<boolean>;
  setOpen: (val: boolean) => void;
}

const HeaderContext = createContext<HeaderContextValue>();

export function HeaderProvider(props: { children: JSX.Element }) {
  const [isOpen, setOpen] = createSignal(false);

  return (
    <HeaderContext.Provider value={{ isOpen, setOpen }}>
      {props.children}
    </HeaderContext.Provider>
  );
}

export function useHeader() {
  const context = useContext(HeaderContext);
  if (!context) throw new Error("useHeader must be used within HeaderProvider");
  return context;
}
