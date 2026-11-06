/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { createSignal } from "solid-js";
import { VncExplorer } from "./components/VncExplorer";
import { VncViewer } from "./components/VncViewer";
import { VncPanel } from "./types";

class MfVncExplorer extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    if (this.dispose) return;

    this.dispose = render(() => <VncExplorer />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("vnc-explorer")) {
  customElements.define("vnc-explorer", MfVncExplorer);
}

type VncPanelParams = VncPanel["params"];

class MfVncViewer extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: VncPanelParams) => void;
  private propsSignal: () => VncPanelParams;

  constructor() {
    super();
    const [props, setProps] = createSignal<VncPanelParams>({ url: "" });
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set mfeProps(newProps: VncPanelParams) {
    this.setProps(newProps);
  }

  get mfeProps(): VncPanelParams {
    return this.propsSignal();
  }

  set params(newParams: VncPanelParams) {
    this.setProps(newParams);
  }

  get params(): VncPanelParams {
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
        <VncViewer url={current.url}/>
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

if (!customElements.get("vnc-viewer")) {
  customElements.define("vnc-viewer", MfVncViewer);
}
