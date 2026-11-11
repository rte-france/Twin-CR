/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { NotificationsPanel } from "./notifications-panel";

class MfNotificationsPanel extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    if (this.dispose) return;

    this.dispose = render(() => <NotificationsPanel />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("notifications-panel")) {
  customElements.define("notifications-panel", MfNotificationsPanel);
}
