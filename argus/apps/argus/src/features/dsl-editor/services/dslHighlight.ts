/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

/**
 * Syntax highlighting for the DSL, matching what the LaTeX reference renders: reserved words, element types,
 * $parameters, strings, comments and numbers.
 *
 * Written as a decorating ViewPlugin rather than a CodeMirror language, because a language needs
 * @codemirror/language, which this app does not depend on. The DSL has no nesting to speak of, so a single pass
 * of a line-oriented tokenizer is enough and there is no tree to maintain.
 *
 * The word lists come from generated/dslKeywords.ts, which is produced from PowerEventDSL.g4 by
 * Orchestrator/DSL/tools/extract_keywords.py, so they cannot drift from the grammar.
 */

import { Decoration, EditorView, ViewPlugin, type DecorationSet, type ViewUpdate } from "@codemirror/view";
import { RangeSetBuilder } from "@codemirror/state";
import { DSL_KEYWORDS, DSL_ELEMENT_TYPES } from "../generated/dslKeywords";

const KEYWORDS = new Set<string>(DSL_KEYWORDS);
const ELEMENT_TYPES = new Set<string>(DSL_ELEMENT_TYPES);

const mark = {
  keyword: Decoration.mark({ class: "cm-dsl-keyword" }),
  type: Decoration.mark({ class: "cm-dsl-type" }),
  variable: Decoration.mark({ class: "cm-dsl-variable" }),
  string: Decoration.mark({ class: "cm-dsl-string" }),
  comment: Decoration.mark({ class: "cm-dsl-comment" }),
  number: Decoration.mark({ class: "cm-dsl-number" }),
};

// Underscores and digits are word characters here: two element types start with a digit
// (2_windings_transformer), and most of the rest contain underscores.
const WORD = /[A-Za-z0-9_]/;

/** Decorate one line, given the document offset of its first character. */
function tokenizeLine(line: string, offset: number, builder: RangeSetBuilder<Decoration>) {
  let i = 0;
  while (i < line.length) {
    const rest = line.slice(i);

    if (rest.startsWith("//")) {
      builder.add(offset + i, offset + line.length, mark.comment);
      return;
    }

    if (line[i] === '"') {
      // An unterminated string still highlights to end of line, which is what it looks like while being typed
      const end = line.indexOf('"', i + 1);
      const stop = end === -1 ? line.length : end + 1;
      builder.add(offset + i, offset + stop, mark.string);
      i = stop;
      continue;
    }

    if (line[i] === "$") {
      let j = i + 1;
      while (j < line.length && WORD.test(line[j])) j++;
      if (j > i + 1) builder.add(offset + i, offset + j, mark.variable);
      i = j > i + 1 ? j : i + 1;
      continue;
    }

    if (WORD.test(line[i])) {
      let j = i;
      while (j < line.length && WORD.test(line[j])) j++;
      const word = line.slice(i, j);
      if (ELEMENT_TYPES.has(word)) {
        builder.add(offset + i, offset + j, mark.type);
      } else if (KEYWORDS.has(word)) {
        builder.add(offset + i, offset + j, mark.keyword);
      } else if (/^[0-9]+(\.[0-9]+)?$/.test(word)) {
        builder.add(offset + i, offset + j, mark.number);
      }
      i = j;
      continue;
    }

    i++;
  }
}

function buildDecorations(view: EditorView): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  // Only what is on screen: the ranges arrive in document order, which is what RangeSetBuilder requires
  for (const { from, to } of view.visibleRanges) {
    for (let pos = from; pos <= to; ) {
      const line = view.state.doc.lineAt(pos);
      tokenizeLine(line.text, line.from, builder);
      pos = line.to + 1;
    }
  }
  return builder.finish();
}

export const dslHighlight = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;

    constructor(view: EditorView) {
      this.decorations = buildDecorations(view);
    }

    update(update: ViewUpdate) {
      if (update.docChanged || update.viewportChanged) {
        this.decorations = buildDecorations(update.view);
      }
    }
  },
  { decorations: (plugin) => plugin.decorations },
);

/** Colours are the ones the LaTeX reference uses, so a script reads the same in both places. */
export const dslHighlightTheme = EditorView.baseTheme({
  ".cm-dsl-keyword": { color: "#0b5394", fontWeight: "bold" },
  ".cm-dsl-type": { color: "#6a3d9a" },
  ".cm-dsl-variable": { color: "#b25000" },
  ".cm-dsl-string": { color: "#8a1f11" },
  ".cm-dsl-comment": { color: "#5f7a5f", fontStyle: "italic" },
  ".cm-dsl-number": { color: "#116644" },
});
