/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { systemRuntime } from "@/config/runtime";
import { DslClient } from "@/services/dsl";
import { GmClient } from "@/services/game-master";
import { LobbyClient } from "@/services/lobby";
import { ScadaClient } from "@/services/scada";
import type { GameSession } from "@/services/session-manager/types";
import { Console, Effect } from "effect";

/**
 * Points the backend clients at the services of a joined session, when the session manager gives their URLs (sessions
 * of the Nomad infrastructure, each with its own services). Without URLs (compose: a single session at fixed
 * addresses), the clients keep their configured URLs.
 *
 * A client that cannot connect does not prevent joining: its error is logged, and its status shows it disconnected.
 */
export const applySessionBackends = (session: GameSession): Promise<void> => {
  const apply = <E>(name: string, url: string | null | undefined, set: (url: string) => Effect.Effect<void, E>) =>
    url
      ? set(url).pipe(
          Effect.catchAll((error) => Console.error(`Could not connect the ${name} backend of the session to ${url}`, error)),
        )
      : Effect.void;

  const program = Effect.gen(function* () {
    const scada = yield* ScadaClient;
    const gm = yield* GmClient;
    const dsl = yield* DslClient;
    const lobby = yield* LobbyClient;

    yield* Effect.all(
      [
        apply("SCADA", session.scada_backend_url, (url) => Effect.zipRight(scada.setUrl(url), scada.connect)),
        apply("GM", session.gm_backend_url, (url) => Effect.zipRight(gm.setUrl(url), gm.connect)),
        apply("DSL", session.dsl_backend_url, (url) => Effect.zipRight(dsl.setUrl(url), dsl.connect)),
        apply("lobby", session.lobby_backend_url, (url) => Effect.zipRight(lobby.setUrl(url), lobby.connect)),
      ],
      { concurrency: "unbounded" },
    );
  });

  return systemRuntime.runPromise(program);
};
