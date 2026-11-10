/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { onMount } from "solid-js";
import type { Component } from "solid-js";
import { ListGroups } from "./ListGroups";
import { ListProjects } from "./ListProjects";
import { createProjectStore } from "../hooks/store";

export const ProjectDashboard: Component = () => {
  const store = createProjectStore();

  onMount(() => {
    store.loadAll();
  });

  return (
    <div class="flex h-full gap-4 p-4">
      <aside class="w-1/4 min-w-70 flex flex-col">
        <div class="flex-1 min-h-0 shadow-sm">
          <ListGroups store={store} />
        </div>
      </aside>
      <section class="flex-1 flex flex-col min-h-0">
        <div class="flex-1 min-h-0 shadow-sm">
          <ListProjects store={store} />
        </div>
      </section>
    </div>
  );
};
