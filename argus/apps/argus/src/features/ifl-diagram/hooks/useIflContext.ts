/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { useContext } from "solid-js";
import { IflContext } from "../types";

export const useIflContext = () => {
  const ctx = useContext(IflContext);
  if (!ctx) throw new Error("useIflContext must be used within a IflProvider");
  return ctx;
};
