/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import * as monaco from "monaco-editor";
import {
  FiAlertTriangle,
  FiCheck,
  FiFileText,
  FiRefreshCw,
  FiSave,
} from "solid-icons/fi";
import {
  type Component,
  createEffect,
  createSignal,
  onCleanup,
  onMount,
  Show,
} from "solid-js";
import type { LobbyStore } from "@/features/workspace/hooks/store";

const EditorPanel: Component<{ store: LobbyStore }> = (props) => {
  const [saveLabel, setSaveLabel] = createSignal<"idle" | "saving" | "saved">(
    "idle",
  );
  let editorContainer: HTMLDivElement | undefined;
  let editorInstance: monaco.editor.IStandaloneCodeEditor | undefined;

  async function handleSave() {
    if (saveLabel() === "saving") return;

    setSaveLabel("saving");
    const ok = await props.store.saveCurrentFile();

    if (ok) {
      setSaveLabel("saved");
      setTimeout(() => setSaveLabel("idle"), 2000);
    } else {
      setSaveLabel("idle");
    }
  }

  onMount(() => {
      if (editorContainer) {
        editorInstance = monaco.editor.create(editorContainer, {
          value: props.store.editorContent(),
          language: "plaintext",
          theme: "vs",
          automaticLayout: true,
          readOnly: props.store.editorDisabled(),
          minimap: { enabled: false },
          wordWrap: "on",
          scrollBeyondLastLine: false,
          fontSize: 13,
          fontFamily:
            'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
          padding: { top: 16 },
          renderLineHighlight: "none",
        });

        editorInstance.addCommand(
          monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
          () => {
            handleSave();
          }
        );

        editorInstance.onDidChangeModelContent(() => {
          const currentValue = editorInstance?.getValue() || "";
          props.store.setEditorContent(currentValue);
        });
      }
    });

  onCleanup(() => {
    editorInstance?.dispose();
  });

  // Remplacer l'effet de réinjection par une vérification stricte
  createEffect(() => {
    const storeValue = props.store.editorContent();
    if (editorInstance && editorInstance.getValue() !== storeValue) {
      // On ne met à jour Monaco que si la source externe change vraiment (ex: changement de fichier)
      const position = editorInstance.getPosition();
      editorInstance.setValue(storeValue);
      if (position) editorInstance.setPosition(position);
    }
  });

  onCleanup(() => {
    editorInstance?.dispose();
  });

  createEffect(() => {
    const storeValue = props.store.editorContent();
    if (editorInstance && editorInstance.getValue() !== storeValue) {
      editorInstance.setValue(storeValue);
    }
  });

  createEffect(() => {
    if (editorInstance) {
      const isDisabled = props.store.editorDisabled();
      editorInstance.updateOptions({ readOnly: isDisabled });

      if (editorContainer) {
        editorContainer.style.opacity = isDisabled ? "0.6" : "1";
        editorContainer.style.pointerEvents = isDisabled ? "none" : "auto";
      }
    }
  });

  return (
    <main class="flex flex-col w-full h-full min-h-0 p-4 bg-gray-50">
      <div class="flex flex-col flex-1 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
          <div class="flex items-center gap-2 font-medium text-gray-700">
            <FiFileText class="text-lg text-blue-600" />
            {props.store.selectedFileName() ?? "No file selected"}
          </div>

          <div class="flex items-center gap-4">
            <Show when={props.store.selectedFileId()}>
              <button
                type="button"
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white transition-colors bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed"
                onClick={handleSave}
                disabled={saveLabel() === "saving"}
              >
                <Show
                  when={saveLabel() === "idle"}
                  fallback={
                    <>
                      <Show
                        when={saveLabel() === "saving"}
                        fallback={<FiCheck class="text-sm" />}
                      >
                        <FiRefreshCw class="text-sm animate-spin" />
                      </Show>
                      {saveLabel() === "saving" ? "Saving..." : "Saved!"}
                    </>
                  }
                >
                  <FiSave class="text-sm" />
                  Save
                </Show>
              </button>
            </Show>
          </div>
        </div>

        <Show when={props.store.stubWarningVisible()}>
          <div class="flex items-start gap-2 px-4 py-3 text-sm text-yellow-800 bg-yellow-50 border-b border-yellow-200">
            <FiAlertTriangle class="text-base shrink-0 mt-0.5" />
            <span>
              This file still has the default auto-generated content (job
              "group1"/"task1"). It is probably not your actual template: edit
              it or select another file before launching a session.
            </span>
          </div>
        </Show>

        <div class="flex-1 relative bg-white min-h-0">
          <Show when={!props.store.editorContent()}>
            <div class="absolute top-4 left-15.5 text-sm font-mono text-gray-400 pointer-events-none z-10">
              Select any text file from the left to edit its content, or write
              here...
            </div>
          </Show>

          <div
            ref={editorContainer}
            class="w-full h-full transition-opacity duration-200"
          />
        </div>
      </div>
    </main>
  );
};

export default EditorPanel;
