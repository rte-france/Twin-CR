/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { createSignal } from "solid-js";
import { NadViewer } from "./components/NadViewer";
import { NadExplorer } from "./components/NadExplorer";
import { createDefaultNad, Nad } from "./types";

class MfNadExplorer extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    if (this.dispose) return;
    this.dispose = render(() => <NadExplorer />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("nad-explorer")) {
  customElements.define("nad-explorer", MfNadExplorer);
}

class MfNetworkAreaDiagram extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: Nad) => void;
  private propsSignal: () => Nad;

  constructor() {
    super();
    const [props, setProps] = createSignal<Nad>(createDefaultNad("empty", "empty"));
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set mfeProps(newProps: Nad) {
    this.setProps(newProps);
  }

  get mfeProps(): Nad {
    return this.propsSignal();
  }

  set params(newParams: Nad) {
    this.setProps(newParams);
  }

  get params(): Nad {
    return this.propsSignal();
  }

  connectedCallback() {
    if (this.dispose) return;

    if (Object.prototype.hasOwnProperty.call(this, "mfeProps")) {
      const value = (this as any).mfeProps;
      delete (this as any).mfeProps;
      this.mfeProps = value;
    }

    this.dispose = render(() => {
      const current = this.propsSignal();
      return (
        <NadViewer {...current}/>
      );
    }, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("nad-viewer")) {
  customElements.define("nad-viewer", MfNetworkAreaDiagram);
}
