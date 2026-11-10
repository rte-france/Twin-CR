/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { Router, Route } from "@solidjs/router";
import { lazy, type ParentProps } from "solid-js";

import { Shell } from "@/app/layout/shell";
import { AuthGuard, RoleGuard } from "@/features/auth";

const Home = lazy(() => import("./home"));
const Projects = lazy(() => import("./projects"));
const Workspace = lazy(() => import("./workspace"));

const DeploySession = lazy(() => import("./deploy-session"));
const JoinSession = lazy(() => import("./join-session"));
const AdminSession = lazy(() => import("./admin-session"));
const WaitingRoom = lazy(() => import("./waiting-room"));

const RouterGuard = (props: ParentProps) => {
  return <Shell>{props.children}</Shell>;
};

const GamemasterGuard = (props: ParentProps) => (
  <RoleGuard role="gamemaster" fallback="/join-session">
    {props.children}
  </RoleGuard>
);

const SupervisorGuard = (props: ParentProps) => (
  <RoleGuard role="supervisor" fallback="/join-session">
    {props.children}
  </RoleGuard>
);

export function AppRouter() {
  return (
    <AuthGuard>
      <Router root={RouterGuard}>
        <Route component={GamemasterGuard}>
          <Route path="/" component={Home} />
          <Route path="/projects" component={Projects} />
          <Route path="/workspace/:projectId/:fileId?" component={Workspace} />
          <Route path="/deploy-session" component={DeploySession} />
        </Route>

        <Route component={SupervisorGuard}>
          <Route path="/admin-session" component={AdminSession} />
        </Route>

        <Route path="/join-session" component={JoinSession} />
        <Route path="/waiting-room/:sessionId" component={WaitingRoom} />
      </Router>
    </AuthGuard>
  );
}
