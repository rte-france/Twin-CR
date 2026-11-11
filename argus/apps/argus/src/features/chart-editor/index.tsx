/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { createSignal } from "solid-js";
import { ChartEditor } from "./components/ChartEditor";
import { CurveViewer } from "./components/CurveViewer";
import { ChartExplorer } from "./components/ChartExplorer";

class MfChartExplorer extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    if (this.dispose) return;
    this.dispose = render(() => <ChartExplorer />, this);
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
      this.innerHTML = "";
    }
  }
}

if (!customElements.get("chart-explorer")) {
  customElements.define("chart-explorer", MfChartExplorer);
}

class MfChartEditor extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: Record<string, any>) => void;
  private propsSignal: () => Record<string, any>;

  constructor() {
    super();
    const [props, setProps] = createSignal<Record<string, any>>({});
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set mfeProps(newProps: Record<string, any>) {
    this.setProps((prev: Record<string, any>) => ({ ...prev, ...newProps }));
  }

  get mfeProps(): Record<string, any> {
    return this.propsSignal();
  }

  set params(newParams: Record<string, any>) {
    this.setProps((prev: Record<string, any>) => ({ ...prev, ...newParams }));
  }

  get params(): Record<string, any> {
    return this.propsSignal();
  }

  connectedCallback() {
    if (this.dispose) return;

    if (Object.prototype.hasOwnProperty.call(this, "mfeProps")) {
      const value = (this as any).mfeProps;
      delete (this as any).mfeProps;
      this.mfeProps = value;
    }
    if (Object.prototype.hasOwnProperty.call(this, "params")) {
      const value = (this as any).params;
      delete (this as any).params;
      this.params = value;
    }

    this.dispose = render(() => {
      const currentProps = this.propsSignal();
      return (
        <ChartEditor
          initialQuery={currentProps.initialQuery}
          dashboardId={currentProps.dashboardId}
        />
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

if (!customElements.get("chart-editor")) {
  customElements.define("chart-editor", MfChartEditor);
}

class MfCurveViewer extends HTMLElement {
  private dispose: (() => void) | null = null;
  private setProps: (props: Record<string, any>) => void;
  private propsSignal: () => Record<string, any>;

  constructor() {
    super();
    const [props, setProps] = createSignal<Record<string, any>>({});
    this.propsSignal = props;
    this.setProps = setProps;
  }

  set mfeProps(newProps: Record<string, any>) {
    this.setProps((prev: Record<string, any>) => ({ ...prev, ...newProps }));
  }

  get mfeProps(): Record<string, any> {
    return this.propsSignal();
  }

  set params(newParams: Record<string, any>) {
    this.setProps((prev: Record<string, any>) => ({ ...prev, ...newParams }));
  }

  get params(): Record<string, any> {
    return this.propsSignal();
  }

  connectedCallback() {
    if (this.dispose) return;

    if (Object.prototype.hasOwnProperty.call(this, "mfeProps")) {
      const value = (this as any).mfeProps;
      delete (this as any).mfeProps;
      this.mfeProps = value;
    }
    if (Object.prototype.hasOwnProperty.call(this, "params")) {
      const value = (this as any).params;
      delete (this as any).params;
      this.params = value;
    }

    this.dispose = render(() => {
      const currentProps = this.propsSignal();
      return (
        <CurveViewer
          title={currentProps.title}
          dashboardId={currentProps.dashboardId}
        />
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

if (!customElements.get("curve-viewer")) {
  customElements.define("curve-viewer", MfCurveViewer);
}
