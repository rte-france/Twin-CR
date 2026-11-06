"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Context detection helpers for DSL autocomplete.

This module centralizes ANTLR-based partial parsing and context inference so
HTTP routers remain thin wrappers around typed completion contexts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Optional

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from ..antlr.PowerEventDSLLexer import PowerEventDSLLexer
from ..antlr.PowerEventDSLParser import PowerEventDSLParser

_TAGGED_LABEL_RE = re.compile(r"\btagged\s+\"([^\"\r\n]*)\"", re.IGNORECASE)
_NODE_LITERAL_RE = re.compile(r"\bnode\s+\"([^\"\r\n]*)\"", re.IGNORECASE)
_LINK_LITERAL_RE = re.compile(
    r"\blink\s+from\s+\"([^\"\r\n]*)\"\s+to\s+\"([^\"\r\n]*)\"",
    re.IGNORECASE,
)

STATIC_PROPERTY_NAME_FALLBACK: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "p0",
        "q0",
        "p",
        "q",
        "target_p",
        "voltage_level_id",
        "substation_id",
        "i",
        "nominal_v",
        "connected",
        "tags",
    }
)

_COMPONENT_TYPE_TEXTS: frozenset[str] = frozenset(
    {
        "switch",
        "line",
        "load",
        "generator",
        "twoWindingsTransformer",
        "threeWindingsTransformer",
        "substation",
        "voltageLevel",
        "busbarSection",
        "battery",
        "shunt",
        "staticVarCompensator",
        "hvdcLine",
        "bus",
        "asset",
        "2_windings_transformer",
        "3_windings_transformer",
    }
)

_TOKEN_ID_TO_LITERAL: dict[int, str] = {}
_LITERAL_TO_TOKEN_ID: dict[str, int] = {}
for _idx, _literal in enumerate(PowerEventDSLLexer.literalNames):
    if not _literal or _literal == "<INVALID>":
        continue
    _text = _literal[1:-1] if _literal.startswith("'") and _literal.endswith("'") else _literal
    if _text:
        _TOKEN_ID_TO_LITERAL[_idx] = _text
        _LITERAL_TO_TOKEN_ID[_text] = _idx


def _literal_to_token_id(text: str) -> int:
    return _LITERAL_TO_TOKEN_ID.get(text, -1)


def _literal_token_set(*literals: str) -> frozenset[int]:
    token_ids = {_literal_to_token_id(literal) for literal in literals}
    return frozenset(token_id for token_id in token_ids if token_id >= 0)


_GRAMMAR_NEXT_OVERRIDE: dict[int, frozenset[int]] = {}
for _token_text, _next_values in {
    "set": ("simulation", "time", "load", "generator"),
    "tagged": ("STRING",),
    "open": ("switch", "line"),
    "close": ("switch", "line"),
    "increase": ("load", "generator"),
    "decrease": ("load", "generator"),
}.items():
    _source_id = _literal_to_token_id(_token_text)
    if _source_id < 0:
        continue
    if _next_values == ("STRING",):
        _targets = frozenset({PowerEventDSLLexer.STRING})
    else:
        _targets = _literal_token_set(*_next_values)
    if _targets:
        _GRAMMAR_NEXT_OVERRIDE[_source_id] = _targets

_STATEMENT_STARTER_IDS: frozenset[int] = _literal_token_set(
    "set",
    "at",
    "when",
    "after",
    "open",
    "close",
    "increase",
    "decrease",
    "apply",
    "clear",
    "change",
)

CompletionKind = Literal[
    "keywords",
    "elements",
    "labels",
    "property_names",
    "property_values",
    "network_nodes",
    "free_text",
]


@dataclass(frozen=True)
class AutocompleteParseState:
    complete_prefix: str
    cursor_prefix: str
    in_open_string: bool
    effective_expected_token_ids: frozenset[int]
    rule_stack: tuple[str, ...]
    tokens: tuple[Any, ...]
    parse_error_count: int


@dataclass(frozen=True)
class AutocompleteContext:
    kind: CompletionKind
    context: Optional[str] = None
    element_type: Optional[str] = None
    component_type_hint: Optional[str] = None
    property_name: Optional[str] = None


class _CapturingErrorListener(ErrorListener):
    """Capture expected-token sets and parser rule stacks for syntax errors."""

    __slots__ = ("_errors",)

    def __init__(self) -> None:
        super().__init__()
        self._errors: list[tuple[set[int], list[str]]] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e) -> None:
        expected: set[int] = set()
        stack: list[str] = []
        if hasattr(recognizer, "getExpectedTokens"):
            try:
                expected = set(recognizer.getExpectedTokens())
            except Exception:  # pragma: no cover
                expected = set()
        if hasattr(recognizer, "getRuleInvocationStack"):
            try:
                stack = list(recognizer.getRuleInvocationStack())
            except Exception:  # pragma: no cover
                stack = []
        self._errors.append((expected, stack))

    @property
    def last_expected(self) -> set[int]:
        return self._errors[-1][0] if self._errors else set()

    @property
    def last_stack(self) -> list[str]:
        return self._errors[-1][1] if self._errors else []

    @property
    def error_count(self) -> int:
        return len(self._errors)


def split_at_cursor(partial: str) -> tuple[str, str, bool]:
    """Split editor text into parser prefix and cursor token prefix."""

    if not partial or partial.isspace():
        return "", "", False

    in_open_string = False
    last_quote = -1
    for idx, ch in enumerate(partial):
        if ch != '"':
            continue
        in_open_string = not in_open_string
        last_quote = idx

    if in_open_string and last_quote >= 0:
        return partial[:last_quote], partial[last_quote + 1 :], True

    for idx in range(len(partial) - 1, -1, -1):
        if partial[idx].isspace():
            return partial[: idx + 1], partial[idx + 1 :], False

    return "", partial, False


def _parse_partial_and_capture_expected(
    text: str,
) -> tuple[set[int], list[str], list[Any], int]:
    if not text or not text.strip():
        return set(), [], [], 0

    stream = InputStream(text)
    lexer = PowerEventDSLLexer(stream)
    lexer.removeErrorListeners()

    token_stream = CommonTokenStream(lexer)
    parser = PowerEventDSLParser(token_stream)
    parser.removeErrorListeners()

    listener = _CapturingErrorListener()
    parser.addErrorListener(listener)
    parser.program()

    token_stream.fill()
    hidden = {PowerEventDSLLexer.WS, PowerEventDSLLexer.COMMENT, -1}
    tokens = [token for token in token_stream.tokens if token.type not in hidden]
    return listener.last_expected, listener.last_stack, tokens, listener.error_count


def _effective_expected(last_expected: set[int], tokens: list[Any], parse_error_count: int) -> frozenset[int]:
    last_token = tokens[-1] if tokens else None
    if last_token and getattr(last_token, "type", None) in _GRAMMAR_NEXT_OVERRIDE:
        return _GRAMMAR_NEXT_OVERRIDE[last_token.type]
    if last_expected:
        return frozenset(last_expected)
    if parse_error_count == 0:
        return _STATEMENT_STARTER_IDS
    return frozenset()


def token_ids_to_literals(token_ids: set[int] | frozenset[int]) -> list[str]:
    mapped = {_TOKEN_ID_TO_LITERAL[token_id] for token_id in token_ids if token_id in _TOKEN_ID_TO_LITERAL}
    return sorted(mapped)


def _infer_component_type_from_tokens(tokens: tuple[Any, ...]) -> Optional[str]:
    for token in reversed(tokens):
        token_text = str(getattr(token, "text", "") or "")
        if token_text in _COMPONENT_TYPE_TEXTS:
            return token_text
    return None


def _infer_element_component_type(rule_stack: tuple[str, ...], tokens: tuple[Any, ...]) -> Optional[str]:
    top_rule = rule_stack[0] if rule_stack else ""
    if top_rule == "switchAction":
        return "switch"
    if top_rule == "lineAction":
        return "line"
    if top_rule == "variable":
        token_texts = [str(getattr(token, "text", "") or "") for token in tokens]
        if "voltageLevel" in token_texts:
            return "voltageLevel"
        if "line" in token_texts:
            return "line"
    return _infer_component_type_from_tokens(tokens)


def _safe_strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _extract_last_string_literal(tokens: tuple[Any, ...]) -> Optional[str]:
    for token in reversed(tokens):
        if getattr(token, "type", None) == PowerEventDSLLexer.STRING:
            token_text = str(getattr(token, "text", "") or "")
            text = _safe_strip_quotes(token_text).strip()
            if text:
                return text
    return None


def _classify_string_context(rule_stack: tuple[str, ...], tokens: tuple[Any, ...]) -> tuple[CompletionKind, str]:
    effective_stack = (
        rule_stack[1:] if rule_stack and rule_stack[0] == "stringAtom" else rule_stack
    )
    top_rule = effective_stack[0] if effective_stack else ""
    last_text = str(getattr(tokens[-1], "text", "") or "") if tokens else ""

    if top_rule == "eventDef" and last_text == "after":
        return "labels", "after_dependency"
    if top_rule == "propertyName":
        return "property_names", "property_name"
    if top_rule == "groupByFilter":
        return "property_values", "property_value"
    if top_rule in {"linkClause", "nodeClause"}:
        return "network_nodes", "network_node"
    if top_rule in {"switchAction", "lineAction", "component", "target", "listItem", "variable"}:
        return "elements", "element_id"
    if top_rule == "tagged":
        return "free_text", "tag_label"
    if top_rule == "regexFilter":
        return "free_text", "regex_pattern"
    if top_rule == "clusterSpec":
        return "free_text", "cluster_label"
    if top_rule == "lawSpec":
        return "free_text", "law_name"
    return "free_text", "string"


def analyze_partial(partial: str) -> tuple[AutocompleteParseState, AutocompleteContext]:
    """Analyze partial DSL input and infer completion context metadata."""

    complete_prefix, cursor_prefix, in_open_string = split_at_cursor(partial)
    last_expected, stack, tokens, parse_error_count = _parse_partial_and_capture_expected(
        complete_prefix
    )
    effective = _effective_expected(last_expected, tokens, parse_error_count)
    state = AutocompleteParseState(
        complete_prefix=complete_prefix,
        cursor_prefix=cursor_prefix,
        in_open_string=in_open_string,
        effective_expected_token_ids=effective,
        rule_stack=tuple(stack),
        tokens=tuple(tokens),
        parse_error_count=parse_error_count,
    )

    if in_open_string and PowerEventDSLLexer.STRING in effective:
        kind, context = _classify_string_context(state.rule_stack, state.tokens)
        if kind == "elements":
            return state, AutocompleteContext(
                kind=kind,
                context=context,
                element_type=_infer_element_component_type(state.rule_stack, state.tokens),
            )
        if kind == "property_names":
            return state, AutocompleteContext(
                kind=kind,
                context=context,
                component_type_hint=_infer_component_type_from_tokens(state.tokens),
            )
        if kind == "property_values":
            return state, AutocompleteContext(
                kind=kind,
                context=context,
                component_type_hint=_infer_component_type_from_tokens(state.tokens),
                property_name=_extract_last_string_literal(state.tokens),
            )
        return state, AutocompleteContext(kind=kind, context=context)

    return state, AutocompleteContext(kind="keywords")


def extract_tagged_labels(text: str, prefix: str, limit: Optional[int]) -> list[str]:
    """Extract previously typed event labels from tagged clauses."""

    labels = {match.group(1).strip() for match in _TAGGED_LABEL_RE.finditer(text)}
    values = []
    for value in labels:
        if value and has_prefix(value, prefix):
            values.append(value)
        if limit and limit > 0 and len(values) >= limit:
            break
    return sorted(values)


def extract_network_nodes_from_text(text: str) -> list[str]:
    """Extract node/link endpoint names from already-typed DSL clauses."""

    values: set[str] = set()
    for match in _NODE_LITERAL_RE.finditer(text):
        node = match.group(1).strip()
        if node:
            values.add(node)
    for match in _LINK_LITERAL_RE.finditer(text):
        src = match.group(1).strip()
        dst = match.group(2).strip()
        if src:
            values.add(src)
        if dst:
            values.add(dst)
    return sorted(values)

def has_prefix(
    value: str,
    prefix: str
) -> bool:
    """Returns whether a str has a given prefix ignoring case"""
    prefix_folded = prefix.casefold()
    return value.casefold().startswith(prefix_folded)
