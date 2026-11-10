/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { createSignal } from "solid-js";
import { SynopticExplorer } from "./components/SynopticExplorer";
import { SynopticViewer } from "./components/SynopticViewer";
import type { SynopticViewerParams } from "./types";

class MfSynopticExplorer extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    if (this.dispose) return;
    this.dispose = render(() => <SynopticExplorer />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("synoptic-explorer")) {
  customElements.define("synoptic-explorer", MfSynopticExplorer);
}

class MfSynopticViewer extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: SynopticViewerParams) => void;
  private propsSignal: () => SynopticViewerParams;

  constructor() {
    super();
    const [props, setProps] = createSignal<SynopticViewerParams>({ name: "" });
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set params(newParams: SynopticViewerParams) {
    this.setProps(newParams || { name: "" });
  }

  get params(): SynopticViewerParams {
    return this.propsSignal();
  }

  set mfeProps(newProps: SynopticViewerParams) {
    this.setProps(newProps || { name: "" });
  }

  get mfeProps(): SynopticViewerParams {
    return this.propsSignal();
  }

  connectedCallback() {
    if (this.dispose) return;
    for (const key of ["mfeProps", "params"]) {
      if (Object.prototype.hasOwnProperty.call(this, key)) {
        const value = (this as any)[key];
        delete (this as any)[key];
        (this as any)[key] = value;
      }
    }
    this.dispose = render(() => <SynopticViewer {...this.propsSignal()} />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("synoptic-viewer")) {
  customElements.define("synoptic-viewer", MfSynopticViewer);
}
