/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { Suspense, Show, createResource, type ParentProps } from "solid-js";
import { initAuth } from "../api/keycloak";
import { Loading } from "./Loading";

const authPromise = initAuth();

export const AuthGuard = (props: ParentProps) => {
  const [isAuthenticated] = createResource(() => authPromise);

  return (
    <Suspense fallback={<Loading />}>
      <Show
        when={isAuthenticated() === true}
        fallback={
          <div style="padding: 2rem; color: #dc2626; font-family: sans-serif;">
            <h1>Authentication Failed</h1>
            <p>You must be logged in to access this application.</p>
            <button
              onClick={() => window.location.reload()}
              style="padding: 0.5rem 1rem; cursor: pointer; margin-top: 1rem; border: 2px solid #dc2626; background: white;"
            >
              Retry
            </button>
          </div>
        }
      >
        {props.children}
      </Show>
    </Suspense>
  );
};
