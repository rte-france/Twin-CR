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
  focusGroupLeft,
  focusGroupRight,
  focusGroupAbove,
  focusGroupBelow,
  toggleMaximize,
  toggleLeftPanel,
  toggleRightPanel,
  toggleLeftBottomPanel,
  toggleRightBottomPanel,
} from "@/app/layout/shell/actions";
import type { EventTree } from "@/types/event.type";

export const EVENTS = {
  argus: {
    tab: {
      next: nextTab,
      prev: prevTab,
    },
    group: {
      left: focusGroupLeft,
      right: focusGroupRight,
      up: focusGroupAbove,
      down: focusGroupBelow,
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
