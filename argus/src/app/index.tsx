/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, onMount } from "solid-js";
import { Route, Router } from "@solidjs/router";
import { Effect, Exit } from "effect";

import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { initAuth, accessToken } from "@/features/auth";
import { WindowManager } from "@/services/window-manager";

import "@/config/extensions";

import { SignIn } from "./routes/sign-in";
import { Home } from "./routes/home";
import { Floating } from "./routes/floating";
import { FloatingLayout } from "./layout/floating";
import { Lobby } from "./routes/lobby";
import { resolveInitialPath, getParentLabelFromUrl } from "./routes/routingUtils";

const RootRoute = () => {
  const token = accessToken();
  if (token) {
    return <Lobby />;
  }
  return <SignIn />;
};

const Routing = () => {
  const initialUrl = resolveInitialPath();

  const initialParent = getParentLabelFromUrl() || "main";

  const [windowInfo, setWindowInfo] = createSignal({
    label: "main",
    isMain: true,
    initialRoute: initialUrl,
    themeSyncId: initialParent,
  });

  onMount(async () => {
    // Only initialise OAuth listener if this is the main window
    const params = new URLSearchParams(window.location.search);
    const isChild = params.has("parent") || params.get("detached") === "true";
    if (!isChild) {
      initAuth();
    }

    const identifyProgram = Effect.gen(function* () {
      const wm = yield* WindowManager;
      const label = yield* wm.getCurrentLabel();
      const isMain = yield* wm.isMain();

      const themeSyncId = getParentLabelFromUrl() || label;

      return { label, isMain, initialRoute: initialUrl, themeSyncId };
    });

    getSystemRuntime().runCallback(identifyProgram, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit)) {
          setWindowInfo(exit.value);
        }
      },
    });
  });

  return (
    <Router url={initialUrl}>
      <Route path="/" component={RootRoute} />
      <Route path="/sign-in" component={SignIn} />
      <Route path="/lobby" component={Lobby} />

      <Route
        path="/home"
        component={() => (
          <Home
            windowLabel={windowInfo().label}
            themeSyncId={windowInfo().themeSyncId}
          />
        )}
      />

      <Route
        path="/panels"
        component={(props) => (
          <FloatingLayout
            windowLabel={windowInfo().label}
            themeSyncId={windowInfo().themeSyncId}
          >
            {props.children}
          </FloatingLayout>
        )}
      >
        <Route
          path="/:id"
          component={() => <Floating parentLabel={windowInfo().themeSyncId} />}
        />
      </Route>

      <Route
        path="/floating"
        component={(props) => (
          <FloatingLayout
            windowLabel={windowInfo().label}
            themeSyncId={windowInfo().themeSyncId}
          >
            {props.children}
          </FloatingLayout>
        )}
      >
        <Route
          path="/:viewType/:id"
          component={() => <Floating parentLabel={windowInfo().themeSyncId} />}
        />
      </Route>
    </Router>
  );
};

export function App() {
  return <Routing />;
}
