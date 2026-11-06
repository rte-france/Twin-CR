"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Autocomplete endpoints for DSL keywords and context-aware DSL suggestions.

This router provides lightweight completion helpers for editor-like clients.
Keyword completions are extracted directly from the ANTLR grammar literals so
changes in ``PowerEventDSL.g4`` are reflected without process restarts.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List, Literal, Optional, Union

from fastapi import APIRouter, Cookie, HTTPException, Query
from pydantic import BaseModel

from ..domain.controllers.global_instances import get_simulation_controller
from ..utils.DSLEngine.antlr.PowerEventDSLLexer import PowerEventDSLLexer
from ..utils.DSLEngine.interpreter.autocomplete_context import (
    STATIC_PROPERTY_NAME_FALLBACK,
    analyze_partial,
    extract_network_nodes_from_text,
    extract_tagged_labels,
    token_ids_to_literals, has_prefix
)
from ..utils.DSLEngine.iidm.properties import get_iidm_properties

router = APIRouter(tags=["Autocomplete"])
logger = logging.getLogger(__name__)

GRAMMAR_FILE_PATH = (
    Path(__file__).resolve().parents[1]
    / "utils"
    / "DSLEngine"
    / "antlr"
    / "PowerEventDSL.g4"
)

_LITERAL_RE = re.compile(r"'((?:\\.|[^'\\])*)'")
_KEYWORD_CACHE_MTIME: float | None = None
_KEYWORD_CACHE: List[str] = []


class _KeywordCompletionResponse(BaseModel):
    kind: Literal["keywords"] = "keywords"
    suggestions: List[str]


class _ElementCompletionResponse(BaseModel):
    kind: Literal["elements"] = "elements"
    element_type: Optional[str] = None
    suggestions: List[str]


class _LabelCompletionResponse(BaseModel):
    kind: Literal["labels"] = "labels"
    suggestions: List[str]


class _PropertyNameCompletionResponse(BaseModel):
    kind: Literal["property_names"] = "property_names"
    component_type_hint: Optional[str] = None
    suggestions: List[str]


class _PropertyValueCompletionResponse(BaseModel):
    kind: Literal["property_values"] = "property_values"
    property_name: Optional[str] = None
    component_type_hint: Optional[str] = None
    suggestions: List[str]


class _NetworkNodeCompletionResponse(BaseModel):
    kind: Literal["network_nodes"] = "network_nodes"
    suggestions: List[str]


class _FreeTextCompletionResponse(BaseModel):
    kind: Literal["free_text"] = "free_text"
    context: str
    suggestions: List[str]


_ContextCompletionResponse = Union[
    _KeywordCompletionResponse,
    _ElementCompletionResponse,
    _LabelCompletionResponse,
    _PropertyNameCompletionResponse,
    _PropertyValueCompletionResponse,
    _NetworkNodeCompletionResponse,
    _FreeTextCompletionResponse,
]


def _strip_grammar_comments(content: str) -> str:
    """
    Remove line/block comments while preserving quoted literals.

    Args:
        content (str): Raw grammar file content.

    Returns:
        str: Grammar text without ``//`` or ``/*...*/`` comments.
    """

    out: List[str] = []
    i = 0
    n = len(content)
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    escape = False

    while i < n:
        ch = content[i]
        nxt = content[i + 1] if i + 1 < n else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                out.append(ch)
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_single_quote:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_double_quote = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch == "'":
            in_single_quote = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double_quote = True
            out.append(ch)
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _extract_literals_from_grammar(grammar_content: str) -> List[str]:
    """
    Extract and deduplicate single-quoted literals preserving declaration order.

    Args:
        grammar_content (str): ANTLR grammar file content.

    Returns:
        List[str]: Ordered list of literal tokens.
    """

    cleaned = _strip_grammar_comments(grammar_content)
    seen: set[str] = set()
    literals: List[str] = []
    for match in _LITERAL_RE.finditer(cleaned):
        value = match.group(1).replace("\\'", "'").replace("\\\\", "\\")
        if value not in seen:
            seen.add(value)
            literals.append(value)
    return literals


def _fallback_literals_from_lexer() -> List[str]:
    """
    Extract literals from the generated lexer as a fallback source.

    Returns:
        List[str]: Ordered unique literal values.
    """

    seen: set[str] = set()
    literals: List[str] = []
    for value in PowerEventDSLLexer.literalNames:
        if not value or value == "<INVALID>":
            continue
        if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
            token = value[1:-1]
        else:
            token = value
        if token not in seen:
            seen.add(token)
            literals.append(token)
    return literals


def _get_keyword_literals() -> List[str]:
    """
    Return grammar literals with mtime-based cache invalidation.

    Returns:
        List[str]: Ordered literals from grammar or lexer fallback.
    """

    global _KEYWORD_CACHE_MTIME, _KEYWORD_CACHE  # pylint: disable=global-statement

    try:
        mtime = GRAMMAR_FILE_PATH.stat().st_mtime
    except OSError:
        if not _KEYWORD_CACHE:
            logger.warning(
                "Grammar file not readable at %s, using lexer literals fallback",
                GRAMMAR_FILE_PATH,
            )
            _KEYWORD_CACHE = _fallback_literals_from_lexer()
            _KEYWORD_CACHE_MTIME = None
        return list(_KEYWORD_CACHE)

    if _KEYWORD_CACHE_MTIME == mtime and _KEYWORD_CACHE:
        return list(_KEYWORD_CACHE)

    try:
        grammar_text = GRAMMAR_FILE_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "Failed to read grammar file %s (%s), using lexer fallback",
            GRAMMAR_FILE_PATH,
            exc,
        )
        _KEYWORD_CACHE = _fallback_literals_from_lexer()
        _KEYWORD_CACHE_MTIME = None
        return list(_KEYWORD_CACHE)

    _KEYWORD_CACHE = _extract_literals_from_grammar(grammar_text)
    _KEYWORD_CACHE_MTIME = mtime
    return list(_KEYWORD_CACHE)

def _get_keywords_limited(prefix: str, limit: Optional[int]) -> List[str]:
    literals = _get_keyword_literals()
    results = []
    for literal in literals:
        if literal and has_prefix(literal, prefix):
            results.append(literal)
        if limit and limit > 0 and len(results) >= limit:
            break
    return sorted(results)

def _keyword_suggestions_from_expected(token_ids: frozenset[int], prefix: str, limit: Optional[int]) -> List[str]:
    """
    Build keyword-like suggestions from parser expected token ids.

    ``STRING`` tokens have no literal name in ANTLR metadata, so expose
    a quote marker to avoid empty completion sets in quote-start contexts.
    """

    suggestions = set(token_ids_to_literals(token_ids))
    if PowerEventDSLLexer.STRING in token_ids:
        suggestions.add('"')
    values = []
    for value in suggestions:
        if value and has_prefix(value, prefix):
            values.append(value)
        if limit and limit > 0 and len(values) >= limit:
            break
    return sorted(values)


def _normalize_non_empty(value: Optional[str]) -> Optional[str]:
    """
    Normalize optional string inputs by stripping whitespace.

    Args:
        value (Optional[str]): Candidate value.

    Returns:
        Optional[str]: Stripped non-empty value, otherwise ``None``.
    """

    if value is None or not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _resolve_artifact_id(
    explicit_artifact_id: Optional[str], iidm_cookie: Optional[str]
) -> Optional[str]:
    """
    Resolve artifact id using query, simulation context, then IIDM cookie.

    Args:
        explicit_artifact_id (Optional[str]): Explicit query argument.
        iidm_cookie (Optional[str]): ``iidm_file_id`` cookie value.

    Returns:
        Optional[str]: Resolved artifact id, if available.
    """

    normalized_query = _normalize_non_empty(explicit_artifact_id)
    if normalized_query:
        return normalized_query

    try:
        simulation_controller = get_simulation_controller()
    except Exception as exc:  # pragma: no cover - defensive path
        logger.debug("Could not access simulation controller for artifact fallback: %s", exc)
        simulation_controller = None

    if simulation_controller is not None:
        controller_artifact = _normalize_non_empty(
            getattr(simulation_controller, "iidm_artifact_id", None)
        )
        if controller_artifact:
            return controller_artifact

        interpreter = getattr(simulation_controller, "interpreter", None)
        interpreter_artifact = _normalize_non_empty(
            getattr(interpreter, "artifact_id", None) if interpreter else None
        )
        if interpreter_artifact:
            return interpreter_artifact

    return _normalize_non_empty(iidm_cookie)


def _get_iidm_components(
    resolved_artifact_id: Optional[str], component_type: Optional[str]
) -> List[dict[str, Any]]:
    """
    Load IIDM components safely. Errors are swallowed for context endpoint use.
    """

    if not resolved_artifact_id or not component_type:
        return []
    try:
        return list(get_iidm_properties(resolved_artifact_id, component_type) or [])
    except Exception as exc:  # pragma: no cover - defensive path
        logger.debug(
            "Context completion IIDM fetch failed for artifact=%s type=%s: %s",
            resolved_artifact_id,
            component_type,
            exc,
        )
        return []


def _extract_component_ids(
    resolved_artifact_id: Optional[str],
    component_type: Optional[str],
    prefix: str,
    limit: Optional[int]
) -> List[str]:
    """
    Return deduplicated, sorted IIDM element ids filtered by prefix.
    """

    components = _get_iidm_components(resolved_artifact_id, component_type)
    values: set[str] = set()
    for component in components:
        component_id = component.get("id") if isinstance(component, dict) else None
        if component_id is None:
            continue
        as_text = str(component_id).strip()
        if as_text and has_prefix(as_text, prefix):
            values.add(as_text)
        if limit and limit > 0 and len(values) >= limit:
            break
    return sorted(values)


def _property_name_suggestions(
    resolved_artifact_id: Optional[str],
    component_type_hint: Optional[str],
    prefix: str,
    limit: Optional[int]
) -> List[str]:
    """
    Suggest property names from IIDM keys with static fallback.
    """

    names = set(STATIC_PROPERTY_NAME_FALLBACK)
    for component in _get_iidm_components(resolved_artifact_id, component_type_hint):
        if isinstance(component, dict):
            names.update(str(key) for key in component.keys() if key)
    values = []
    for value in names:
        if value and has_prefix(value, prefix):
            values.append(value)
        if limit and limit > 0 and len(values) >= limit:
            break
    return sorted(values)


def _property_value_suggestions(
    resolved_artifact_id: Optional[str],
    component_type_hint: Optional[str],
    property_name: Optional[str],
    prefix: str,
    limit: Optional[int]
) -> List[str]:
    """
    Suggest distinct property values from IIDM records.
    """

    if not property_name:
        return []

    values: set[str] = set()
    for component in _get_iidm_components(resolved_artifact_id, component_type_hint):
        if not isinstance(component, dict):
            continue
        raw_value = component.get(property_name)
        if isinstance(raw_value, (list, tuple, set)):
            for item in raw_value:
                as_text = str(item).strip()
                if as_text:
                    values.add(as_text)
            continue
        if raw_value is None:
            continue
        as_text = str(raw_value).strip()
        if as_text and has_prefix(as_text, prefix):
            values.add(as_text)
        if limit and limit > 0 and len(values) >= limit:
            break
    return sorted(values)


def _network_node_suggestions(
    complete_prefix: str,
    resolved_artifact_id: Optional[str],
    prefix: str,
    limit: Optional[int]
) -> List[str]:
    """
    Suggest network nodes from local DSL text and IIDM node-like types.
    """

    values: set[str] = set(extract_network_nodes_from_text(complete_prefix))
    values = set([value for value in values if has_prefix(value, prefix)])
    for component_type in ("bus", "busbarSection", "voltageLevel"):
        # Limit the number of results after local DSL selection rather than before
        # Limit is distributed equally on the manifolds rather than dynamically attributed to avoid single types returns
        for value in _extract_component_ids(resolved_artifact_id, component_type, prefix, limit//3):
            values.add(value)

    return sorted(values)


@router.get("/completions/keywords")
def get_keyword_completions(
    partial: str = Query("", description="Case-insensitive completion prefix"),
    limit: int = Query(10, description="Maximum number of keyword to return, negative numbers return the whole list."),
) -> List[str]:
    """
    Return DSL literals whose value matches ``partial`` as a prefix.
    """

    return _get_keywords_limited(partial, limit)


@router.get("/completions/elements")
def get_element_completions(
    component_type: str = Query(..., alias="type", description="IIDM component type"),
    partial: str = Query("", description="Case-insensitive completion prefix"),
    artifact_id: Optional[str] = Query(
        None, description="Optional IIDM artifact id override"
    ),
    iidm_file_id: Optional[str] = Cookie(
        None, description="Fallback artifact context cookie"
    ),
    limit: int = Query(10, description="Maximum number of elements to return."),
) -> List[str]:
    """
    Return IIDM element identifiers matching ``partial`` for a component type.
    """

    resolved_artifact_id = _resolve_artifact_id(artifact_id, iidm_file_id)
    if not resolved_artifact_id:
        raise HTTPException(
            status_code=400,
            detail="Missing IIDM artifact context. Provide artifact_id or upload IIDM first.",
        )

    try:
        components = get_iidm_properties(
            resolved_artifact_id,
            component_type,
        )
    except Exception as exc:
        logger.error(
            "Failed to get IIDM properties for artifact=%s type=%s: %s",
            resolved_artifact_id,
            component_type,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve IIDM properties for element completion.",
        ) from exc

    matching_ids: set[str] = set()
    for component in components or []:
        component_id = component.get("id") if isinstance(component, dict) else None
        if component_id is None:
            continue
        value = str(component_id).strip()
        if value and has_prefix(value, partial):
            matching_ids.add(value)
        if limit and limit > 0 and len(matching_ids) >= limit:
            break

    return sorted(matching_ids)


@router.get("/completions/context", response_model=_ContextCompletionResponse)
def get_context_completions(
    partial: str = Query("", description="Partial DSL source up to cursor"),
    artifact_id: Optional[str] = Query(
        None, description="Optional IIDM artifact id override"
    ),
    iidm_file_id: Optional[str] = Cookie(
        None, description="Fallback artifact context cookie"
    ),
    limit: int = Query(10, description="Maximum number of suggestions to return."),
) -> _ContextCompletionResponse:
    """
    Return context-aware completions based on ANTLR expected tokens and rule stack.
    """

    state, context = analyze_partial(partial)

    if not state.complete_prefix:
        return _KeywordCompletionResponse(
            suggestions=_get_keywords_limited(state.cursor_prefix, limit)
        )

    if context.kind == "keywords":
        keyword_suggestions = _keyword_suggestions_from_expected(
            state.effective_expected_token_ids, state.cursor_prefix, limit
        )
        return _KeywordCompletionResponse(suggestions=keyword_suggestions)

    resolved_artifact_id = _resolve_artifact_id(artifact_id, iidm_file_id)

    if context.kind == "elements":
        suggestions = _extract_component_ids(
            resolved_artifact_id,
            context.element_type,
            state.cursor_prefix,
            limit
        )
        return _ElementCompletionResponse(
            element_type=context.element_type,
            suggestions=suggestions,
        )

    if context.kind == "labels":
        labels = extract_tagged_labels(state.complete_prefix, state.cursor_prefix, limit)
        return _LabelCompletionResponse(
            suggestions=labels
        )

    if context.kind == "property_names":
        return _PropertyNameCompletionResponse(
            component_type_hint=context.component_type_hint,
            suggestions=_property_name_suggestions(
                resolved_artifact_id,
                context.component_type_hint,
                state.cursor_prefix,
                limit
            ),
        )

    if context.kind == "property_values":
        return _PropertyValueCompletionResponse(
            property_name=context.property_name,
            component_type_hint=context.component_type_hint,
            suggestions=_property_value_suggestions(
                resolved_artifact_id,
                context.component_type_hint,
                context.property_name,
                state.cursor_prefix,
                limit
            ),
        )

    if context.kind == "network_nodes":
        return _NetworkNodeCompletionResponse(
            suggestions=_network_node_suggestions(
                state.complete_prefix,
                resolved_artifact_id,
                state.cursor_prefix,
                limit
            )
        )

    return _FreeTextCompletionResponse(context=context.context or "string", suggestions=[])
