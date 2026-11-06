"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Utilities for translating DSL actions into persistent event-store entries.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def build_action_payload(action: dict) -> Dict[str, Any]:
    """
    Extract the payload portion of a DSL action suitable for persistence.

    Args:
        action (dict): Prepared action dictionary.

    Returns:
        Dict[str, Any]: Payload containing only relevant attributes.
    """
    if not isinstance(action, dict):
        return {}
    if str(action.get("type", "")).lower() == "print":
        return {"message": action.get("message", "")}
    if str(action.get("type", "")).lower() == "function_completion":
        payload: Dict[str, Any] = {
            "function_name": action.get("function_name"),
            "child_event_ids": action.get("child_event_ids") or [],
            "expanded": bool(action.get("expanded")),
        }
        if action.get("metadata") is not None:
            payload["metadata"] = action.get("metadata")
        return payload
    if str(action.get("type", "")).lower() == "invoke_function":
        payload: Dict[str, Any] = {
            "function_name": action.get("function_name"),
            "bindings": action.get("bindings") or {},
            "checked": bool(action.get("checked")),
        }
        if action.get("completion_event_id") is not None:
            payload["completion_event_id"] = action.get("completion_event_id")
        if action.get("metadata") is not None:
            payload["metadata"] = action.get("metadata")
        return payload
    if str(action.get("type", "")).lower() == "change_network_characteristics":
        payload: Dict[str, Any] = {
            "links": action.get("links") or [],
            "nodes": action.get("nodes") or [],
        }
        if action.get("delay_function") is not None:
            payload["delay_function"] = action.get("delay_function")
        if action.get("drop_function") is not None:
            payload["drop_function"] = action.get("drop_function")
        if action.get("corruption_functions") is not None:
            payload["corruption_functions"] = action.get("corruption_functions")
        if action.get("t_start_from_now") is not None:
            payload["t_start_from_now"] = action.get("t_start_from_now")
        if action.get("t_start") is not None:
            payload["t_start"] = action.get("t_start")
        if action.get("metadata") is not None:
            payload["metadata"] = action.get("metadata")
        return payload
    payload: Dict[str, Any] = {}

    def _maybe_set(key: str, value):
        """
        Assign a key inside the payload if the value is meaningful.

        Args:
            key (str): Payload key.
            value: Candidate value to set.
        """
        if value is None:
            return
        if isinstance(value, list) and not value:
            return
        payload[key] = value

    try:
        if "percentage" in action:
            _maybe_set("percentage", float(action["percentage"]))
    except (TypeError, ValueError):
        pass

    try:
        if "target_percentage" in action:
            _maybe_set("target_percentage", float(action["target_percentage"]))
    except (TypeError, ValueError):
        pass

    _maybe_set("attribute", action.get("attribute"))
    _maybe_set("operation", action.get("operation"))
    _maybe_set("element_type", action.get("element_type"))
    _maybe_set("targets", action.get("targets"))
    _maybe_set("measurement_keys", action.get("measurement_keys"))
    _maybe_set("setpoint", action.get("setpoint"))
    _maybe_set("setpoints", action.get("setpoints"))
    _maybe_set("target_spec", action.get("target_spec"))
    return payload


def persist_event(
    ctx,
    *,
    event_id: str,
    action: dict,
    time_spec: str,
    at: float | None = None,
    interval_start: float | None = None,
    interval_end: float | None = None,
    law: str | None = None,
    condition_expr=None,
    dependency_id: str | None = None,
    due_at: float | None = None,
    tag: str | None = None,
) -> None:
    """
    Persist a DSL action into the event store with idempotency safeguards.

    Args:
        ctx: Interpreter context exposing `event_store`, `simulation_name`,
            and `event_source`.
        event_id (str): Identifier assigned to the stored event.
        action (dict): Prepared DSL action dictionary.
        time_spec (str): Time specification (point, interval, condition).
        at (Optional[float]): Point event time.
        interval_start (Optional[float]): Interval start.
        interval_end (Optional[float]): Interval end.
        law (Optional[str]): Interval law descriptor.
        condition_expr: Serialized condition expression when applicable.
        dependency_id (Optional[str]): Upstream dependency id.
    """
    if ctx.event_store is None:
        return
    try:
        source = getattr(ctx, "event_source", "dsl")
        evt_type = action.get("type", "unknown")
        target = action.get("id") if "id" in action else action.get("target")
        payload = build_action_payload(action)
        metadata = action.get("metadata") if isinstance(action, dict) else None

        def _normalize_target(t):
            """Normalize the event target for idempotency calculations."""
            if isinstance(t, list):
                try:
                    return ",".join(sorted(map(str, t)))
                except Exception:
                    return ",".join(map(str, t))
            return str(t)

        idempotency_target = _normalize_target(target)
        if evt_type == "change_network_characteristics":
            canonical = {
                "links": payload.get("links"),
                "nodes": payload.get("nodes"),
                "delay_function": payload.get("delay_function"),
                "drop_function": payload.get("drop_function"),
                "corruption_functions": payload.get("corruption_functions"),
                "t_start": payload.get("t_start"),
                "t_start_from_now": payload.get("t_start_from_now"),
            }
            idempotency_target = json.dumps(canonical, sort_keys=True, default=str)
        elif evt_type == "print":
            canonical = {
                "message": payload.get("message"),
                "condition_expr": condition_expr,
            }
            idempotency_target = json.dumps(canonical, sort_keys=True, default=str)

        idemp = (
            f"dsl:{ctx.simulation_name}:{evt_type}:{idempotency_target}:"
            f"{at or interval_start}:{interval_end or ''}:{law or ''}:"
            f"{dependency_id or ''}:{tag or ''}"
        )
        status_override = None
        if time_spec == "point" and dependency_id and not at:
            status_override = "pending"

        computed_due_at = due_at
        if computed_due_at is None and time_spec in {"point", "interval"}:
            lead = getattr(ctx, "time_step", None)
            try:
                lead_val = float(lead) if lead is not None else 0.0
            except (TypeError, ValueError):
                lead_val = 0.0
            if lead_val <= 0:
                lead_val = 1e-3
            anchor = at if time_spec == "point" else interval_start
            if anchor is not None:
                computed_due_at = max(0.0, float(anchor) - lead_val)

        ctx.event_store.enqueue_event(
            source=source,
            type=evt_type,
            target=target,
            payload=payload or None,
            metadata=metadata,
            time_spec=time_spec,
            at=at,
            interval_start=interval_start,
            interval_end=interval_end,
            law=law,
            condition_expr=condition_expr,
            dependency_id=dependency_id,
            event_id=event_id,
            idempotency_key=idemp,
            simulation=ctx.simulation_name,
            status=status_override,
            due_at=computed_due_at,
            tag=tag,
        )
    except Exception:
        # Best-effort; do not raise in interpreter flow
        pass
