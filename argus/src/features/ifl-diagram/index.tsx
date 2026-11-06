/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { createSignal } from "solid-js";
import { IflViewer } from "./components/IflViewer";
import { IflExplorer } from "./components/IflExplorer";
import { IflParams } from "./types";

class MfIflExplorer extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    if (this.dispose) return;
    this.dispose = render(() => <IflExplorer />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("ifl-explorer")) {
  customElements.define("ifl-explorer", MfIflExplorer);
}

class MfNetworkAreaDiagram extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: IflParams) => void;
  private propsSignal: () => IflParams;

  constructor() {
    super();
    const [props, setProps] = createSignal<IflParams>({ id: "empty", name: "empty", nodeIds: [], depth: 0 });
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set mfeProps(newProps: IflParams) {
    this.setProps(newProps);
  }

  get mfeProps(): IflParams {
    return this.propsSignal();
  }

  set params(newParams: IflParams) {
    this.setProps(newParams);
  }

  get params(): IflParams {
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
        <IflViewer {...current}/>
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

if (!customElements.get("ifl-viewer")) {
  customElements.define("ifl-viewer", MfNetworkAreaDiagram);
}
