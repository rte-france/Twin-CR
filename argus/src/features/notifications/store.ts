/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal } from "solid-js";
import { Notification, NewNotification } from "./types";

const [notifications, setNotifications] = createSignal<Notification[]>([]);

export function addNotification(input: NewNotification) {
  const newNotif: Notification = {
    id: crypto.randomUUID(),
    message: input.message,
    type: input.type ?? "info",
    date: Date.now(),
  };

  setNotifications((current) => [...current, newNotif]);
}

export { notifications };
