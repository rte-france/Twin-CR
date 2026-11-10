/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  closeActivePanel,
  nextTab,
  prevTab,
  toggleMaximize,
  toggleLeftPanel,
  toggleRightPanel,
  toggleLeftBottomPanel,
  toggleRightBottomPanel,
} from "@/app/layout/shell/actions";
import type { EventTree } from "@/types/event.type";

/**
 * Global declarative event schema and handlers.
 * Nested keys form the event identifier (e.g. argus:tab:next).
 */
export const EVENTS = {
  argus: {
    tab: {
      next: nextTab,
      prev: prevTab,
    },
    panel: {
      close: closeActivePanel,
      maximize: {
        toggle: toggleMaximize,
      },
      left: {
        toggle: toggleLeftPanel,
      },
      right: {
        toggle: toggleRightPanel,
      },
      "left-bottom": {
        toggle: toggleLeftBottomPanel,
      },
      "right-bottom": {
        toggle: toggleRightBottomPanel,
      },
    },
  },
} as const satisfies EventTree;
