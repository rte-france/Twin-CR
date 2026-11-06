/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { createSignal } from "solid-js";
import { ScadaCommandsTable } from "./components/ScadaCommandsTable";

class MfScadaCommands extends HTMLElement {
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
    if (Object.prototype.hasOwnProperty.call(this, "mfeProps")) {
      const value = (this as any).mfeProps;
      delete (this as any).mfeProps;
      this.mfeProps = value;
    }

    this.dispose = render(
      () => <ScadaCommandsTable {...this.propsSignal()} />,
      this,
    );
  }

  disconnectedCallback() {
    if (this.dispose) {
      this.dispose();
      this.dispose = null;
    }
  }
}

if (!customElements.get("scada-commands")) {
  customElements.define("scada-commands", MfScadaCommands);
}
