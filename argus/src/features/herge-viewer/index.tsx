/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { HergeViewer } from "./components/HergeViewer";
import { createSignal } from "solid-js";
import { HergeExplorer } from "./components/HergeExplorer";

class MfHergeViewer extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: any) => void;
  private propsSignal: () => any;

  constructor() {
    super();
    const [props, setProps] = createSignal<Record<string, any>>({});
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set mfeProps(newProps: any) {
    this.setProps(newProps || {});
  }

  get mfeProps() {
    return this.propsSignal();
  }

  connectedCallback() {
    if (this.dispose) return;

    if (Object.prototype.hasOwnProperty.call(this, "mfeProps")) {
      const value = (this as any).mfeProps;
      delete (this as any).mfeProps;
      this.mfeProps = value;
    }

    this.dispose = render(() => <HergeViewer {...this.propsSignal()} />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("herge-viewer")) {
  customElements.define("herge-viewer", MfHergeViewer);
}

class MfHergeExplorer extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    if (this.dispose) return;
    this.dispose = render(() => <HergeExplorer />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("herge-explorer")) {
  customElements.define("herge-explorer", MfHergeExplorer);
}
