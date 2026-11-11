/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { createSignal } from "solid-js";
import { Effect, Fiber } from "effect";
import { NetworkPropertiesExplorer } from "./components/NetworkPropertiesExplorer";
import { NetworkPropertiesViewer } from "./components/NetworkPropertiesViewer";
import { defaultComponentTypeConfig, NetworkPropertiesPanel } from "./types";

class MfNetworkPropertiesExplorer extends HTMLElement {
  private dispose: (() => void) | null = null;
  connectedCallback() {
    if (this.dispose) return;
    this.dispose = render(() => <NetworkPropertiesExplorer />, this);
  }
  disconnectedCallback() {
    if (this.dispose) { this.dispose(); this.dispose = null; this.innerHTML = ""; }
  }
}
if (!customElements.get("network-properties-explorer")) {
  customElements.define("network-properties-explorer", MfNetworkPropertiesExplorer);
}

type ViewerParams = NetworkPropertiesPanel["params"];

class MfNetworkPropertiesViewer extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: ViewerParams) => void;
  private propsSignal: () => ViewerParams;
  private modeFiber: Fiber.RuntimeFiber<void, any> | undefined;

  constructor() {
    super();
    const [props, setProps] = createSignal<ViewerParams>({
      componentType: "",
      config: defaultComponentTypeConfig(),
    });
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set params(newParams: ViewerParams) { this.setProps(newParams); }
  get params(): ViewerParams { return this.propsSignal(); }
  set mfeProps(newProps: ViewerParams) { this.setProps(newProps); }
  get mfeProps(): ViewerParams { return this.propsSignal(); }

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
        <NetworkPropertiesViewer
          componentType={current.componentType}
          config={current.config}
        />
      );
    }, this);
  }

  disconnectedCallback() {
    if (this.modeFiber) Effect.runFork(Fiber.interrupt(this.modeFiber));
    if (this.dispose) { this.dispose(); this.dispose = null; this.innerHTML = ""; }
  }
}
if (!customElements.get("network-properties-viewer")) {
  customElements.define("network-properties-viewer", MfNetworkPropertiesViewer);
}
