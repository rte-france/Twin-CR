/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show } from "solid-js";

/**
 * What a rejected call should say on screen. `apiFetch` puts FastAPI's
 * `detail` in the message, so this is the backend's own wording.
 */
export function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

type ErrorPanelProps = {
  message: string | null;
  class?: string;
};

export function ErrorPanel(props: ErrorPanelProps) {
  return (
    <Show when={props.message}>
      {(message) => (
        <p
          role="alert"
          class={`border-l-2 border-red-600 bg-red-50 px-3 py-2 text-xs text-red-800 ${props.class ?? ""}`}
        >
          {message()}
        </p>
      )}
    </Show>
  );
}
