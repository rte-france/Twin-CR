"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import Optional

from .event_processor import apply_interval_law


def start_simulation(ctx) -> None:
    if ctx.duration is None or ctx.time_step is None:
        raise ValueError("Simulation duration or time step not set")
    ctx.current_time = 0.0
    ctx.start_time = datetime.now()
    ctx.end_time = ctx.start_time + timedelta(seconds=ctx.duration)

    def event_sort_key(e):
        ts = e["time_spec"]
        return ts["interval"][0] if isinstance(ts, dict) and "interval" in ts else ts

    ctx.time_events.sort(key=event_sort_key)


def get_current_step_actions(ctx, new_time: float, system_state=None):
    if system_state is None:
        system_state = {}
    if new_time < ctx.current_time:
        raise ValueError("New time must be >= current simulation time")
    if new_time > ctx.duration:
        new_time = ctx.duration

    ctx.current_time = new_time

    current_actions = []
    newly_completed = set()

    def mark_completed(event_id):
        pending = [event_id]
        while pending:
            current_id = pending.pop()
            if not current_id:
                continue
            if current_id in newly_completed or current_id in ctx.completed_events:
                continue
            newly_completed.add(current_id)
            if hasattr(ctx, "_resolve_function_completion_ids"):
                pending.extend(ctx._resolve_function_completion_ids(current_id))

    def handle_due_action(event_id, action):
        if (
            isinstance(action, dict)
            and str(action.get("type") or "").lower() == "invoke_function"
            and hasattr(ctx, "_invoke_function_action")
        ):
            expansion = ctx._invoke_function_action(
                action,
                invocation_time=ctx.current_time,
                system_state=system_state,
            )
            for expanded_action in expansion.get("actions", []) or []:
                current_actions.append(expanded_action)
            mark_completed(event_id)
            for completion_id in expansion.get("completed_ids", []) or []:
                mark_completed(completion_id)
            return
        current_actions.append(action)
        mark_completed(event_id)

    eps = ctx._epsilon()
    for event in ctx.time_events:
        ts = event["time_spec"]
        if isinstance(ts, dict) and "interval" in ts:
            start, end = ts["interval"]
            if start <= ctx.current_time <= end:
                action_copy = copy.deepcopy(event["action"])
                law = ts.get("law")
                base_template = (
                    event.get("template") if isinstance(event, dict) else None
                )
                if base_template is None:
                    base_template = event["action"]
                apply_interval_law(
                    action=action_copy,
                    base_action=base_template,
                    law=law,
                    start=start,
                    end=end,
                    current_time=ctx.current_time,
                    time_step=ctx.time_step,
                )
                current_actions.append(
                    {
                        "action": action_copy,
                        "law": law,
                        "interval_start": start,
                        "interval_end": end,
                    }
                )
                if ctx.current_time == end:
                    mark_completed(event["id"])
        elif abs(ts - ctx.current_time) < eps:
            handle_due_action(event["id"], event["action"])

    for event in ctx.condition_events:
        if ctx.evaluate_dynamic_expression(event["dynamic_expr"], system_state):
            handle_due_action(event["id"], event["action"])

    updated_dependent_events = []
    step_delay = ctx.time_step if ctx.time_step else ctx._epsilon()
    for event in ctx.dependent_events:
        ready_at = event.get("ready_at")
        dependency_id = event["dependency"]
        if ready_at is not None:
            if ctx.current_time + ctx._epsilon() >= ready_at:
                handle_due_action(event["id"], event["action"])
            else:
                updated_dependent_events.append(event)
            continue

        if dependency_id in newly_completed:
            event["ready_at"] = ctx.current_time + step_delay
            updated_dependent_events.append(event)
        elif dependency_id in ctx.completed_events:
            handle_due_action(event["id"], event["action"])
        else:
            updated_dependent_events.append(event)

    ctx.completed_events.update(newly_completed)
    ctx.dependent_events = updated_dependent_events

    enriched_actions = []
    for action in current_actions:
        if isinstance(action, dict) and "action" in action:
            prepared = ctx.prepare_action(action["action"], system_state)
            action["action"] = prepared
            enriched_actions.append(action)
        else:
            enriched_actions.append(ctx.prepare_action(action, system_state))

    if ctx.event_store is not None:
        from ..persistence.event_store import build_action_payload

        for item in enriched_actions:
            candidate = (
                item["action"] if isinstance(item, dict) and "action" in item else item
            )
            if not isinstance(candidate, dict):
                continue
            metadata = candidate.get("metadata") or {}
            event_id = metadata.get("event_id")
            if not event_id:
                continue
            payload = build_action_payload(candidate)
            try:
                ctx.event_store.update_payload(event_id, payload or None)
            except Exception:
                pass

    return {
        "current_time": ctx.current_time,
        "actions": enriched_actions,
        "status": "running" if ctx.current_time < ctx.duration else "simulation_ended",
    }
