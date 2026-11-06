/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import {
  createSignal,
  createEffect,
  onMount,
  onCleanup,
  Show,
  untrack,
} from "solid-js";
import { EditorView, basicSetup } from "codemirror";
import { dslHighlight, dslHighlightTheme } from "../services/dslHighlight";
import { FiPlay, FiCheck, FiAlertTriangle, FiX } from "solid-icons/fi";
import { FaSolidSpinner } from "solid-icons/fa";
import { Effect, Exit } from "effect";
import { systemRuntime } from "@/config/runtime";
import { describeDslError } from "@/services/dsl";
import { DslService } from "../services";
import { Button } from "@kobalte/core/button";

export const DslEditor = () => {
  const [loading, setLoading] = createSignal(true);
  const [dslText, setDslText] = createSignal("");
  const [savedContent, setSavedContent] = createSignal("");
  const [isExecuting, setIsExecuting] = createSignal(false);
  const [executed, setExecuted] = createSignal(false);
  const [executeError, setExecuteError] = createSignal<string | null>(null);

  let editorContainerRef!: HTMLDivElement;
  let viewRef: EditorView | null = null;

  const isDirty = () => dslText() !== savedContent();

  onMount(() => {
    const program = Effect.gen(function* () {
      const dslService = yield* DslService;
      return yield* dslService.getInitialDsl;
    }).pipe(
      Effect.catchAll((err) => {
        console.error("Failed to load the initial DSL script:", err);
        return Effect.succeed("");
      }),
    );

    const cancel = systemRuntime.runCallback(program, {
      onExit: (exit) => {
        if (Exit.isSuccess(exit)) {
          const text = exit.value;
          setDslText(text);
          setSavedContent(text);
        }
        setLoading(false);
      },
    });

    onCleanup(() => cancel());
  });

  const executeCommand = () => {
    if (!viewRef || isExecuting()) return;

    setIsExecuting(true);
    setExecuteError(null);
    const currentText = viewRef.state.doc.toString();

    const executeProgram = Effect.gen(function* () {
      const dslService = yield* DslService;
      yield* dslService.sendDslCommand(currentText);
    });

    systemRuntime.runCallback(executeProgram, {
      onExit: (exit) => {
        setIsExecuting(false);
        if (Exit.isSuccess(exit)) {
          setExecuted(true);
          setTimeout(() => setExecuted(false), 2000);
        } else {
          setExecuteError(
            exit.cause._tag === "Fail"
              ? describeDslError(exit.cause.error)
              : "The script could not be sent to the DSL engine.",
          );
        }
      },
    });
  };

  createEffect(() => {
    if (loading() || !editorContainerRef || viewRef) return;

    viewRef = new EditorView({
      doc: untrack(dslText),
      extensions: [
        basicSetup,
        dslHighlight,
        dslHighlightTheme,
        EditorView.domEventHandlers({
          keydown: (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "s") {
              event.preventDefault();
              executeCommand();
              return true;
            }
            return false;
          },
        }),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const newText = update.state.doc.toString();
            setDslText(newText);
          }
        }),
      ],
      parent: editorContainerRef,
    });

    onCleanup(() => {
      viewRef?.destroy();
      viewRef = null;
    });
  });

  return (
    <Show
      when={!loading()}
      fallback={
        <div class="flex items-center justify-center h-full bg-bg text-fg">
          <FaSolidSpinner class="animate-spin text-sidebar-active size-6" />
        </div>
      }
    >
      <div class="h-full flex flex-col bg-bg text-fg">
        <div class="flex items-center justify-between bg-sidebar-bg px-4 py-2 border-b border-divider">
          <h2 class="text-sm font-medium flex items-center gap-2 text-fg">
            <Show when={isDirty()}>
              <span
                class="w-2 h-2 rounded-full bg-sidebar-active"
                title="Edited since it was loaded. Executing sends modified the script to the engine, it does not save it."
              />
            </Show>
            DSL Script
          </h2>

          <Button
            onClick={executeCommand}
            disabled={isExecuting()}
            title="Sends the entire script as a new DSL command: already-executed statements will run again."
            class="inline-flex items-center justify-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors bg-download-btn-bg text-download-btn-color hover:bg-download-btn-bg-hover disabled:opacity-50 disabled:cursor-not-allowed border border-download-btn-border"
          >
            <Show
              when={!isExecuting()}
              fallback={<FaSolidSpinner class="animate-spin size-4" />}
            >
              <Show
                when={!executed()}
                fallback={<FiCheck class="size-4 text-toast-border-success" />}
              >
                <FiPlay class="size-4" />
              </Show>
            </Show>
            <span class="hidden sm:inline">
              {isExecuting() ? "Executing..." : executed() ? "Executed" : "Execute"}
            </span>
          </Button>
        </div>

        <div class="flex items-center gap-2 bg-sidebar-bg px-4 py-1.5 border-b border-divider text-xs text-warning-icon">
          <FiAlertTriangle class="size-3.5 shrink-0" />
          <span>
            The init script is launched at execution and should not be executed a second time.
          </span>
        </div>

        <Show when={executeError()}>
          <div class="flex items-start gap-2 bg-sidebar-bg px-4 py-1.5 border-b border-divider text-xs text-toast-border-error">
            <FiAlertTriangle class="size-3.5 shrink-0 mt-0.5" />
            <span class="flex-1 font-mono break-all">{executeError()}</span>
            <button
              type="button"
              onClick={() => setExecuteError(null)}
              class="shrink-0 opacity-70 hover:opacity-100 cursor-pointer"
              title="Dismiss"
            >
              <FiX class="size-3.5" />
            </button>
          </div>
        </Show>

        <div
          ref={editorContainerRef}
          class="flex-1 overflow-auto outline-none [&>.cm-editor]:h-full [&>.cm-editor]:outline-none"
        />
      </div>
    </Show>
  );
};
