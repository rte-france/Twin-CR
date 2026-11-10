/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

const MOCK_TEMPLATES = [
  { id: "t1", groupName: "Frontend", templateName: "React SPA Boilerplate", status: "ready" },
  { id: "t2", groupName: "Backend", templateName: "Node.js Microservice", status: "pending" },
];

const MOCK_STATIONS = [
  { id: "s1", name: "Station Alpha", group: "Group A", status: "waiting", requiresKey: false },
  { id: "s2", name: "Station Beta", group: "Group A", status: "in-progress", requiresKey: true },
];

const MOCK_WAITING_ROOM = {
  incoming: [{ id: "p1", name: "User A", isReady: false }, { id: "p2", name: "User B", isReady: true }],
  supervisors: [{ id: "p4", name: "Admin_01", isReady: true }],
  gamemasters: [null, null],
  operators: [{ id: "p5", name: "Player_Alpha", isReady: true }, null, null]
};

export const SessionAPI = {
  async fetchTemplates() {
    await new Promise(r => setTimeout(r, 400)); // Fake latency
    return MOCK_TEMPLATES;
  },

  async fetchTemplateDetails(id: string) {
    await new Promise(r => setTimeout(r, 200));
    return {
      ...MOCK_TEMPLATES.find(t => t.id === id),
      fields: [
        { id: "f1", label: "Project Name", value: "app-" + id, type: "text" },
        { id: "f2", label: "Target", value: "Production", type: "select", options: ["Dev", "Production"] }
      ]
    };
  },

  async fetchStations() {
    await new Promise(r => setTimeout(r, 400));
    return MOCK_STATIONS;
  },

  async fetchWaitingRoom(sessionId: string) {
    await new Promise(r => setTimeout(r, 500));
    return { sessionId, ...MOCK_WAITING_ROOM };
  }
};
