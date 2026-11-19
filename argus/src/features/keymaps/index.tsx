/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { KeymapsSettings } from "./components/KeymapsSettings";

class MfKeymapsSettings extends HTMLElement {
  private dispose: (() => void) | null = null;

  constructor() {
    super();
  }

  connectedCallback() {
    this.dispose = render(() => <KeymapsSettings />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("panel-keymaps")) {
  customElements.define("panel-keymaps", MfKeymapsSettings);
}

export * from "./components/KeymapsSettings";
export * from "./components/KeymapItem";
export * from "./hooks/useKeymapSettings";
