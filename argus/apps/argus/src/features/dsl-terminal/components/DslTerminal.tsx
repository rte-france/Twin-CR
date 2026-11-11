/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, createEffect, For, onCleanup, batch } from "solid-js";
import { useDslCommand } from "../hooks/useDslCommand";

type LogEntry = {
  id: string;
  type: "input" | "success" | "error" | "system";
  text: string;
  timestamp: Date;
};

export function DslTerminal() {
  const { sendCommand, dslAutocomplete, isLoading, error, isSuccess } =
    useDslCommand();

  const [logs, setLogs] = createSignal<LogEntry[]>([]);
  const [input, setInput] = createSignal("");
  const [suggestions, setSuggestions] = createSignal<string[]>([]);
  const [replaceFrom, setReplaceFrom] = createSignal(0);
  const [caret, setCaret] = createSignal(0);
  const [suggestionIndex, setSuggestionIndex] = createSignal(0);

  const [historyIndex, setHistoryIndex] = createSignal(-1);
  const [draft, setDraft] = createSignal("");

  const [history, setHistory] = createSignal<string[]>(
    JSON.parse(localStorage.getItem("dsl_history") || "[]"),
  );

  let bottomRef!: HTMLDivElement;
  let inputRef!: HTMLTextAreaElement;

  // --- Helpers ---
  const formatTime = (date: Date) =>
    `[${date.toLocaleTimeString("en-US", { hour12: false })}]`;

  const addLog = (type: LogEntry["type"], text: string) => {
    setLogs((prev) => [
      ...prev,
      { id: crypto.randomUUID(), type, text, timestamp: new Date() },
    ]);
  };

  // --- Effects ---

  // Sauvegarde de l'historique en local
  createEffect(() => {
    localStorage.setItem("dsl_history", JSON.stringify(history()));
  });

  // Auto-scroll vers le bas lors de nouveaux logs
  createEffect(() => {
    logs();
    bottomRef?.scrollIntoView({ behavior: "smooth" });
  });

  // Message de succès après exécution API
  createEffect(() => {
    if (isSuccess()) addLog("success", "Command executed successfully.");
  });

  const syncCaret = () => setCaret(inputRef?.selectionStart ?? input().length);

  /**
   * End of the word the cursor sits in, so completing from its middle replaces the whole word rather than
   * leaving its tail behind. Mirrors what the engine treats as one token: inside a string the word runs to the
   * closing quote, outside it to the end of the identifier.
   */
  const wordEnd = (text: string, from: number) => {
    const insideString = (text.slice(0, from).match(/"/g) ?? []).length % 2 === 1;
    if (insideString) {
      const close = text.indexOf('"', from);
      return close === -1 ? text.length : close;
    }
    let end = from;
    while (end < text.length && /[A-Za-z0-9_]/.test(text[end])) end++;
    return end;
  };

  /** Replaces the text and puts the cursor where the caller wants it, once the controlled value has landed. */
  const setInputWithCaret = (text: string, position: number) => {
    // Batch setInput and setCaret to avoid calling the autocomplete on the new text with the old caret
    batch(() => {
      setInput(text);
      setCaret(position);
    });
    queueMicrotask(() => inputRef?.setSelectionRange(position, position));
  };

  // Reactive autocompletion: on what precedes the cursor
  createEffect(() => {
    const partial = input().slice(0, caret());
    if (!partial) {
      setSuggestions([]);
      return;
    }

    const cancel = dslAutocomplete(partial, (response) => {
      if (input().slice(0, caret()) !== partial) return;

      if (response && Array.isArray(response.suggestions)) {
        setSuggestions(response.suggestions);
        setReplaceFrom(response.replace_from ?? partial.length);
        setSuggestionIndex(0);
      } else {
        setSuggestions([]);
      }
    });

    onCleanup(() => cancel());
  });

  // Gestion des erreurs API
  createEffect(() => {
    const err = error();
    if (err) {
      let cleanMessage = "";
      if (err._tag === "HttpError") {
        const payload = err.body || err.message;
        cleanMessage =
          typeof payload === "object"
            ? JSON.stringify(payload, null, 2)
            : String(payload);
        addLog("error", `[API Error ${err.status}]\n${cleanMessage}`);
      } else {
        addLog("error", `[${err._tag}]\n${(err as any).reason || err.message}`);
      }
    }
  });

  // --- Actions ---

  const executeCommand = (cmd: string) => {
    const trimmedCmd = cmd.trim();
    if (!trimmedCmd) return;

    // Ajout visuel immédiat dans le terminal
    addLog("input", trimmedCmd);

    // Mise à jour de l'historique (évite les doublons consécutifs)
    setHistory((prev) => {
      const last = prev[prev.length - 1];
      const newHistory = last === trimmedCmd ? prev : [...prev, trimmedCmd];
      return newHistory.slice(-50);
    });

    // Reset de l'état d'input
    setHistoryIndex(-1);
    setDraft("");
    setInputWithCaret("", 0);
    setSuggestions([]);

    // Envoi effectif
    sendCommand(trimmedCmd);
  };

  // Suggestion is a full word (potentially with quotes) + replaceFrom() is where to write this word, replacing the existing partial word but not the rest of the line.
  const applySuggestion = (suggestion: string) => {
    const text = input();
    let tail = text.slice(wordEnd(text, caret()));
    // A quoted suggestion brings its own closing quote, so the one the cursor is sitting inside goes
    if (suggestion.startsWith('"') && tail.startsWith('"')) tail = tail.slice(1);
    // A space only where the line does not already continue with one, or with punctuation that closes the slot
    const inserted = suggestion + (tail === "" || /^[^\s,;)\]]/.test(tail) ? " " : "");
    setInputWithCaret(
      text.slice(0, replaceFrom()) + inserted + tail,
      replaceFrom() + inserted.length,
    );
    setSuggestions([]);
    inputRef?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    // Navigation dans les suggestions
    if (suggestions().length > 0) {
      if (e.shiftKey && (e.key === "ArrowRight" || e.key === "ArrowLeft")) {
        e.preventDefault();
        const step = e.key === "ArrowRight" ? 1 : suggestions().length - 1;
        setSuggestionIndex((prev) => (prev + step) % suggestions().length);
        return;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        applySuggestion(suggestions()[suggestionIndex()]);
        return;
      }
      if (e.key === "Escape") {
        setSuggestions([]);
        return;
      }
    }

    // Exécution
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      executeCommand(input());
    }

    // Navigation Historique
    else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (history().length > 0) {
        if (historyIndex() === -1) setDraft(input());
        const newIdx =
          historyIndex() === -1
            ? history().length - 1
            : Math.max(0, historyIndex() - 1);
        setHistoryIndex(newIdx);
        setInputWithCaret(history()[newIdx], history()[newIdx].length);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex() !== -1) {
        const newIdx = historyIndex() + 1;
        if (newIdx >= history().length) {
          setHistoryIndex(-1);
          setInputWithCaret(draft(), draft().length);
        } else {
          setHistoryIndex(newIdx);
          setInputWithCaret(history()[newIdx], history()[newIdx].length);
        }
      }
    }
  };

  return (
    <div
      class="flex flex-col w-full h-full min-h-0 bg-sidebar-bg text-code-text font-mono overflow-hidden"
      onClick={() => inputRef?.focus()}
    >
      {/* Zone des Logs */}
      <div class="flex-1 overflow-y-auto p-4 space-y-2 min-h-0">
        <For each={logs()}>
          {(log) => (
            <div class="flex gap-3 text-sm leading-relaxed whitespace-pre-wrap break-all">
              <span class="text-sidebar-non-existant shrink-0 select-none">
                {formatTime(log.timestamp)}
              </span>
              <div class="flex-1">
                {log.type === "input" && (
                  <span class="text-links font-semibold">
                    <span class="mr-2 select-none text-warning-icon">❯</span>
                    {log.text}
                  </span>
                )}
                {log.type === "system" && (
                  <span class="text-sidebar-fg italic">{log.text}</span>
                )}
                {log.type === "success" && (
                  <span class="text-toast-border-success">✔ {log.text}</span>
                )}
                {log.type === "error" && (
                  <span class="text-toast-border-error font-medium">
                    ✖ {log.text}
                  </span>
                )}
              </div>
            </div>
          )}
        </For>
        <div ref={bottomRef} />
      </div>

      {/* Barre d'input et Suggestions */}
      <div class="relative">
        <div class="absolute bottom-full left-0 w-full px-4 mb-2 flex flex-wrap gap-2 items-center">
          <For each={suggestions()}>
            {(suggestion, index) => (
              <div
                onClick={(e) => {
                  e.stopPropagation();
                  applySuggestion(suggestion);
                }}
                class="px-2 py-1 rounded text-xs cursor-pointer transition-colors border border-pre-border flex items-center gap-2"
                classList={{
                  "bg-links text-white": index() === suggestionIndex(),
                  "bg-bg text-sidebar-fg": index() !== suggestionIndex(),
                }}
              >
                <span>{suggestion}</span>
              </div>
            )}
          </For>
          {suggestions().length > 0 && (
            <span class="text-xs text-sidebar-non-existant select-none ml-1">
              shift+←/→ to choose, tab to insert, esc to dismiss
            </span>
          )}
        </div>

        <div class="p-4 border-t border-pre-border bg-bg flex gap-2 items-start shrink-0">
          <span class="text-warning-icon mt-0.5 select-none">❯</span>
          <textarea
            ref={inputRef}
            value={input()}
            onInput={(e) =>
              batch(() => {
                setInput(e.currentTarget.value);
                syncCaret();
              })
            }
            onKeyDown={handleKeyDown}
            onKeyUp={syncCaret}
            onClick={syncCaret}
            onSelect={syncCaret}
            disabled={isLoading()}
            placeholder="DSL Command... (Ctrl+Enter)"
            class="flex-1 bg-transparent outline-none resize-none text-fg placeholder:text-sidebar-non-existant min-h-[24px] max-h-[200px]"
            rows={input().split("\n").length || 1}
          />
        </div>
      </div>
    </div>
  );
}
