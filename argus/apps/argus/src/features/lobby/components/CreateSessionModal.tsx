/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Show, onMount, onCleanup, createSignal } from "solid-js";
import { ErrorPanel, errorMessage } from "./ErrorPanel";
import { createSession } from "@/services/session-manager";

type CreateSessionModalProps = {
  open: boolean;
  sessionName: string;
  dslFile: string;
  configPath: string;
  templateId: number;
  onSessionNameChange: (value: string) => void;
  onDslFileChange: (value: string) => void;
  onConfigPathChange: (value: string) => void;
  onClose: () => void;
};

export function CreateSessionModal(props: CreateSessionModalProps) {
  const [creationInProgress, setCreationInProgress] = createSignal<boolean>(false);
  const isCreateDisabled = () => props.sessionName === "" || creationInProgress();
  const [error, setError] = createSignal<string | null>(null);
  const [okMessage, setOkMessage] = createSignal<string | null>(null);

  onMount(() => {
    const handler = (e: KeyboardEvent) => {
      if (props.open) {
        if (e.key === "Escape") {
          props.onClose();
        }
        if (e.key === "Enter" && !isCreateDisabled()) {
          void createSessionAction();
        }
      }
    };
    window.addEventListener("keydown", handler);
    onCleanup(() => window.removeEventListener("keydown", handler));
  });

  const closeAction = () => {
    setOkMessage(null);
    setError(null);
    props.onClose();
  }

  const createSessionAction = async () => {
    try {
      setCreationInProgress(true);
      await createSession({
        name: props.sessionName,
        dsl_name: props.dslFile,
        config_toml_name: props.configPath,
        templateId:props.templateId
      });
      setOkMessage("Session created");
      await new Promise((resolve) => setTimeout(resolve, 800));
      closeAction();
    } catch (err) {
      console.error("Error during session creation:", err);
      setError(errorMessage(err));
    }
    finally {
      setCreationInProgress(false);
    }
  }

  return (
    <Show when={props.open}>
      <div class="fixed inset-0 flex items-center justify-center bg-black/20 backdrop-blur-sm">
        <div class="bg-white shadow-lg w-96 p-5 flex flex-col gap-4">
          <h2 class="text-sm font-semibold text-gray-800">Create Session</h2>

          <div class="flex flex-col gap-2 text-sm">
            <label class="text-xs text-gray-500">Session name</label>
            <input
              placeholder="Session name"
              class="border border-gray-300 rounded px-2 py-1"
              value={props.sessionName}
              onInput={(e) => props.onSessionNameChange(e.currentTarget.value)}
            />

            <label class="text-xs text-gray-500">DSL file</label>
            <input
              placeholder="DSL file"
              class="border border-gray-300 rounded px-2 py-1"
              value={props.dslFile}
              onInput={(e) => props.onDslFileChange(e.currentTarget.value)}
            />

            <label class="text-xs text-gray-500">Config path</label>
            <input
              placeholder="Config path"
              class="border border-gray-300 rounded px-2 py-1"
              value={props.configPath}
              onInput={(e) => props.onConfigPathChange(e.currentTarget.value)}
            />
          </div>

          <ErrorPanel message={error()} class="mb-3" />

          <div class="flex justify-end gap-2">
            <Show when={okMessage()}>
                <p class={`border-l-2 border-green-600 bg-green-50 px-2 py-1 text-xs text-green-900`}>
                  {okMessage()}
                </p>
            </Show>

            <button
              class="bg-gray-200 px-3 py-1 text-xs enabled:hover:bg-gray-300 disabled:opacity-50"
              onClick={closeAction}
            >
              Cancel
            </button>

            <button
              class="px-3 py-1 bg-slate-800 enabled:hover:bg-cyan-600 text-white font-mono text-xs font-bold tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={isCreateDisabled()}
              onClick={createSessionAction}
            >
              Create Session
            </button>
          </div>
        </div>
      </div>
    </Show>
  );
}
