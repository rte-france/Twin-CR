/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { render } from "solid-js/web";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { AlarmWindow } from "./components/AlarmWindow";
import { startAlarmSounds } from "./sound";
import { openAlarmWindow } from "./components/AlarmBadge";
import { OverloadMonitor, openOverloadMonitor } from "./components/OverloadMonitor";
import { CENTRAL_READY_EVENT } from "@/utils/openInCentral";

/**
 * Alarm and event windows and OverloadMonitor, fed by the alarm service of the current backend.
 * The alarm store and the sounds run in the main window from startup, whether the alarm window is open or not.
 */
const isMainWindow = () => {
  try {
    return getCurrentWindow().label === "main";
  } catch {
    return true;  // Outside Tauri (browser)
  }
};

if (isMainWindow()) {
  startAlarmSounds();
  // The alarm window and the OverloadMonitor are always open: reopened whenever the central dock is (re)created,
  // the alarm window last so that it has the focus
  window.addEventListener(CENTRAL_READY_EVENT, () => {
    openOverloadMonitor();
    openAlarmWindow();
  });
}

const defineWindow = (tag: string, variant: "alarms" | "events") => {
  class AlarmWindowElement extends HTMLElement {
    private dispose: (() => void) | null = null;

    connectedCallback() {
      this.style.display = "block";
      this.style.height = "100%";
      this.dispose = render(() => <AlarmWindow variant={variant} />, this);
    }

    disconnectedCallback() {
      this.dispose?.();
      this.dispose = null;
    }
  }
  if (!customElements.get(tag)) {
    customElements.define(tag, AlarmWindowElement);
  }
};

defineWindow("alarm-list", "alarms");
defineWindow("event-list", "events");

class OverloadMonitorElement extends HTMLElement {
  private dispose: (() => void) | null = null;

  connectedCallback() {
    this.style.display = "block";
    this.style.height = "100%";
    this.dispose = render(() => <OverloadMonitor />, this);
  }

  disconnectedCallback() {
    this.dispose?.();
    this.dispose = null;
  }
}
if (!customElements.get("overload-monitor")) {
  customElements.define("overload-monitor", OverloadMonitorElement);
}
