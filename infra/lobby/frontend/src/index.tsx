/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { render } from "solid-js/web";
import { ErrorBoundary } from "solid-js";
import { AppRouter } from "./app/router";

import "./styles/index.css";

render(
  () => (
    <ErrorBoundary
      fallback={(err) => (
        <div style="padding: 2rem; color: #dc2626; font-family: sans-serif; max-width: 800px; margin: 0 auto;">
          <h1 style="font-size: 1.5rem; font-weight: bold; margin-bottom: 1rem;">Fatal Error</h1>
          <div style="background-color: #fef2f2; padding: 1rem; border: 1px solid #f87171;">
            <pre style="white-space: pre-wrap; word-break: break-all;">
              {err?.error || err?.message || JSON.stringify(err) || "Unknown error"}
            </pre>
          </div>
        </div>
      )}
    >
      <AppRouter />
    </ErrorBoundary>
  ),
  document.getElementById("root") as HTMLElement
);
