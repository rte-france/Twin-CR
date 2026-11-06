"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Utility helpers to produce simulator control payloads outside of REST entrypoints.
"""

from __future__ import annotations

import copy
import logging
from typing import List, Optional, Set, Tuple

from ..domain.controllers.global_instances import (
    get_event_store,
    get_simulation_controller,
)
from ..utils.clock import ClockRegressionError, set_current_time
from ..routers import sim_control
from .value_cache import snapshot as value_snapshot
from ..utils.interval_scaling import apply_interval_law_scaling


def _action_event_id(candidate) -> str | None:
    """
    Extract the originating event id from a prepared action.

    Args:
        candidate: Action dictionary possibly containing metadata.

    Returns:
        Optional[str]: Event identifier when present.
    """
    if not isinstance(candidate, dict):
        return None
    metadata = candidate.get("metadata") or {}
    event_id = metadata.get("event_id")
    return str(event_id) if event_id else None


def _split_action_setpoints_for_basis(
    action: dict,
) -> Tuple[Optional[dict], Optional[dict]]:
    """
    Split setpoints into ready and pending groups when measurement bases are missing.

    Args:
        action (dict): Prepared action dictionary.

    Returns:
        Tuple[Optional[dict], Optional[dict]]:
            ready action (setpoints not waiting for measurements) and pending action
            (setpoints lacking absolute values despite a measurement key).
    """
    if not isinstance(action, dict):
        return action, None
    setpoints = action.get("setpoints") or []
    if not setpoints:
        return action, None

    ready_setpoints = []
    pending_setpoints = []
    for sp in setpoints:
        if sp.get("measurement_key") and sp.get("absolute_value") is None:
            pending_setpoints.append(sp)
        else:
            ready_setpoints.append(sp)

    if not pending_setpoints:
        return action, None

    for sp in pending_setpoints:
        logger.warning("Missing value for %s", sp)

    ready_action = None
    if ready_setpoints:
        ready_action = dict(action)
        ready_action["setpoints"] = ready_setpoints

    pending_action = dict(action)
    pending_action["setpoints"] = pending_setpoints

    return ready_action, pending_action


def _log_pending_action(event_id: str | None, action: dict) -> None:
    """
    Emit a debug log describing actions waiting for measurement bases.

    Args:
        event_id (Optional[str]): Associated event identifier.
        action (dict): Action pending measurement data.
    """
    if not logger.isEnabledFor(logging.DEBUG):
        return
    details = {
        "event_id": event_id,
        "targets": action.get("targets") or action.get("target"),
        "measurement_keys": [
            sp.get("measurement_key") for sp in action.get("setpoints") or []
        ],
        "absolute_values": [
            sp.get("absolute_value") for sp in action.get("setpoints") or []
        ],
    }
    logger.debug("Deferring command until basis arrives: %s", details)


def _log_ready_action(event_id: str | None, action: dict) -> None:
    """
    Emit a debug log for actions that are ready to generate commands.

    Args:
        event_id (Optional[str]): Event identifier associated with the action.
        action (dict): Prepared action dictionary.
    """
    if not logger.isEnabledFor(logging.DEBUG):
        return
    details = {
        "event_id": event_id,
        "targets": action.get("targets") or action.get("target"),
        "measurement_keys": [
            sp.get("measurement_key") for sp in action.get("setpoints") or []
        ],
        "absolute_values": [
            sp.get("absolute_value") for sp in action.get("setpoints") or []
        ],
    }
    logger.debug("Ready for command generation: %s", details)


logger = logging.getLogger(__name__)


class SimulationNotInitializedError(RuntimeError):
    """Raised when simulator control queries are executed before DSL initialization."""


def compute_simulator_control_commands(
    current_time: float,
) -> Tuple[List[dict], str, Set[str]]:
    """Return simulator-control v2 commands and completion ids using the EventStore only."""

    simulation_controller = get_simulation_controller()
    interpreter = simulation_controller.interpreter

    if interpreter is None:
        raise SimulationNotInitializedError("Simulation not initialized.")

    event_store = get_event_store()

    try:
        set_current_time(simulation_controller.simulation_name, current_time)
    except ClockRegressionError:
        raise

    try:
        interpreter.current_time = current_time
    except Exception:
        pass

    eps = max(1e-3, (interpreter.time_step or 0) / 10.0)
    try:
        lead = float(getattr(interpreter, "time_step", None) or 0.0)
    except (TypeError, ValueError):
        lead = 0.0
    if lead <= 0:
        lead = eps
    effective_time = current_time + lead

    try:
        delay = interpreter.time_step or eps
        event_store.promote_ready_events(
            current_time,
            simulation=simulation_controller.simulation_name,
            delay=delay,
        )
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.debug("Failed to promote ready events at time %s: %s", current_time, exc)

    due = event_store.events_due(
        current_time,
        eps,
        simulation=simulation_controller.simulation_name,
    )

    processed_point_events = getattr(
        simulation_controller, "completed_point_events", set()
    )
    if processed_point_events:
        filtered_points = []
        for evt in due.get("points", []):
            evt_id = evt.get("id")
            time_spec = str(evt.get("time_spec") or "").lower()
            if evt_id and time_spec == "point" and evt_id in processed_point_events:
                continue
            filtered_points.append(evt)
        due["points"] = filtered_points

    raw_actions, raw_user_controls, raw_trainer_controls, point_ids, completion_ids = (
        sim_control._partition_due_events(  # pylint: disable=protected-access
            due,
            current_time,
        )
    )

    system_state = value_snapshot()

    waiting_point_event_ids: set[str] = set()
    waiting_condition_event_ids: set[str] = set()
    ready_candidates: list[dict] = []
    pending_candidates: list[dict] = []

    completed_interval_ids: set[str] = set()
    if interpreter and raw_actions:
        time_step = lead
        for item in raw_actions:
            if not isinstance(item, dict):
                continue
            action = item.get("action") if "action" in item else item
            if isinstance(action, dict):
                op = str(action.get("operation") or "").lower()
                typ = str(action.get("type") or "").lower()
                if op == "set" or typ.startswith("set_"):
                    continue
            apply_interval_law_scaling(item, effective_time, time_step)

        prepared_actions = []
        for item in raw_actions:
            if isinstance(item, dict) and "action" in item:
                if "interval_start" in item:
                    interval_end = item.get("interval_end")
                    if interval_end is not None:
                        try:
                            if current_time > float(interval_end):
                                event_id = _action_event_id(item.get("action"))
                                if event_id:
                                    completed_interval_ids.add(event_id)
                                continue
                        except (TypeError, ValueError):
                            pass
                prepared = interpreter.prepare_action(item["action"], system_state)
                event_id = _action_event_id(prepared)
                ready_action, pending_action = _split_action_setpoints_for_basis(prepared)
                interval_law = str(item.get("law") or "").lower()
                needs_from_value = False
                if "interval_start" in item and interval_law == "linear":
                    op = str(prepared.get("operation") or "").lower()
                    typ = str(prepared.get("type") or "").lower()
                    if op == "set" or typ.startswith("set_"):
                        setpoints = prepared.get("setpoints") or []
                        if setpoints:
                            for entry in setpoints:
                                if not isinstance(entry, dict):
                                    continue
                                if entry.get("measurement_key") and entry.get("from_value") is None:
                                    needs_from_value = True
                                    break
                        else:
                            setpoint = prepared.get("setpoint")
                            if isinstance(setpoint, dict):
                                if setpoint.get("measurement_key") and setpoint.get("from_value") is None:
                                    needs_from_value = True
                if pending_action:
                    if event_id:
                        waiting_point_event_ids.add(event_id)
                    _log_pending_action(event_id, pending_action)
                    pending_candidates.append(pending_action)
                if not ready_action:
                    continue
                if needs_from_value:
                    _log_pending_action(event_id, prepared)
                    pending_candidates.append(prepared)
                    continue
                container = dict(item)
                container["action"] = ready_action
                if "interval_start" in container:
                    op = str(ready_action.get("operation") or "").lower()
                    typ = str(ready_action.get("type") or "").lower()
                    if op == "set" or typ.startswith("set_"):
                        apply_interval_law_scaling(
                            container, effective_time, time_step
                        )
                prepared_actions.append(container)
                ready_candidates.append(ready_action)
                _log_ready_action(event_id, ready_action)
            else:
                prepared = interpreter.prepare_action(item, system_state)
                event_id = _action_event_id(prepared)
                ready_action, pending_action = _split_action_setpoints_for_basis(prepared)
                if pending_action:
                    if event_id:
                        waiting_point_event_ids.add(event_id)
                    _log_pending_action(event_id, pending_action)
                    pending_candidates.append(pending_action)
                if not ready_action:
                    continue
                prepared_actions.append(ready_action)
                ready_candidates.append(ready_action)
                _log_ready_action(event_id, ready_action)
        raw_actions = prepared_actions

    if interpreter and raw_trainer_controls:
        prepared_controls = []

        for ctrl in raw_trainer_controls:
            if ctrl.setpoint is not None:
                if "basis_value" in ctrl.setpoint and ctrl.setpoint["basis_value"] is None:
                    waiting_point_event_ids.add(ctrl.metadata["event_id"])
                    continue
            prepared_controls.append(ctrl)
        # If a Control is deferred, all Control elements with same event_id should align
        raw_trainer_controls = [ctrl for ctrl in prepared_controls if ctrl.metadata["event_id"] not in waiting_point_event_ids]

    condition_actions, condition_event_ids = _evaluate_condition_actions(
        interpreter,
        system_state,
        current_time=current_time,
    )
    condition_completion_ids: list[str] = []
    if interpreter and condition_actions:
        for action in condition_actions:
            event_id = _action_event_id(action)
            prepared_action = interpreter.prepare_action(action, system_state)
            ready_action, pending_action = _split_action_setpoints_for_basis(
                prepared_action
            )
            if pending_action and event_id:
                waiting_condition_event_ids.add(event_id)
                interpreter.completed_events.discard(event_id)
            if pending_action:
                _log_pending_action(event_id, pending_action)
                pending_candidates.append(pending_action)
            if not ready_action:
                continue
            raw_actions.append({"action": ready_action})
            ready_candidates.append(ready_action)
            if event_id:
                condition_completion_ids.append(event_id)
            _log_ready_action(event_id, ready_action)
    elif condition_event_ids:
        condition_completion_ids = list(condition_event_ids)

    all_candidates = ready_candidates + pending_candidates

    if interpreter and all_candidates:
        payload_updates = []
        for candidate in all_candidates:
            if not isinstance(candidate, dict):
                continue
            event_id = _action_event_id(candidate)
            if not event_id:
                continue
            payload = interpreter._build_action_payload(candidate)
            payload_updates.append((event_id, payload or None))

        if payload_updates:
            try:
                event_store.update_payloads_batch(payload_updates)
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.debug("Failed to batch update payloads: %s", exc)

    if condition_completion_ids:
        point_ids.extend(condition_completion_ids)

    if completed_interval_ids:
        try:
            event_store.mark_completed(completed_interval_ids)
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.debug(
                "Failed to mark interval events completed: %s",
                exc,
            )

    if waiting_point_event_ids:
        logger.debug(
            "Holding %d point events until basis available: %s",
            len(waiting_point_event_ids),
            sorted(waiting_point_event_ids),
        )
        point_ids = [
            pid for pid in point_ids if not pid or pid not in waiting_point_event_ids
        ]

        if interpreter is not None:
            next_due = current_time + max(interpreter.time_step or 0.0, eps)
        else:
            next_due = current_time + eps
        try:
            event_store.reschedule_point_events(
                waiting_point_event_ids, next_due, lead_time=(interpreter.time_step or eps)
            )
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.debug(
                "Failed to reschedule waiting events %s: %s",
                waiting_point_event_ids,
                exc,
            )
    elif waiting_condition_event_ids:
        logger.debug(
            "Waiting on %d condition events for basis values: %s",
            len(waiting_condition_event_ids),
            sorted(waiting_condition_event_ids),
        )

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Building commands from %d raw actions", len(raw_actions))

    lead = interpreter.time_step or eps
    default_start_time = current_time + lead
    # Ensure interval-derived actions carry the absolute time they execute on this tick
    # Interval t_start stays scheduled; dispatch lead is handled via due_at

    cmds = sim_control._to_v2_commands_from_inputs(  # pylint: disable=protected-access
        raw_actions,
        raw_trainer_controls,
        raw_user_controls,
        default_start_time=default_start_time,
        interval_lead=lead,
        current_time=current_time,
    )

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Computed %d commands (pending: %d waiting events)",
            len(cmds),
            len(waiting_point_event_ids) + len(waiting_condition_event_ids),
        )

    return cmds, simulation_controller.simulation_name, set(completion_ids)


__all__ = [
    "SimulationNotInitializedError",
    "compute_simulator_control_commands",
]


def _evaluate_condition_actions(interpreter, system_state, current_time: float):
    """
    Evaluate conditional DSL events and return actions that are triggered.

    Args:
        interpreter: DSL interpreter containing condition events.
        system_state: Snapshot of measurement values for evaluation.

    Returns:
        Tuple[List[dict], List[str]]: Triggered actions and their event ids.
    """
    triggered_actions = []
    triggered_ids = []
    delay = None
    try:
        delay = getattr(interpreter, "time_step", None)
    except Exception:
        delay = None
    try:
        delay_val = float(delay) if delay is not None else 0.0
    except (TypeError, ValueError):
        delay_val = 0.0
    if delay_val <= 0:
        delay_val = max(1e-3, delay_val)
    for event in getattr(interpreter, "condition_events", []) or []:
        event_id = event.get("id")
        if not event_id or event_id in getattr(interpreter, "completed_events", set()):
            continue
        expr = event.get("dynamic_expr")
        try:
            result = interpreter.evaluate_dynamic_expression(expr, system_state)
            logger.debug(
                "Condition event %s evaluated to %s with state %s",
                event_id,
                result,
                system_state,
            )
            if result:
                action_copy = copy.deepcopy(event.get("action", {}))
                try:
                    action_copy.setdefault("t_start", float(current_time + delay_val))
                except Exception:
                    pass
                triggered_actions.append(action_copy)
                triggered_ids.append(event_id)
        except Exception as exc:
            logger.debug("Failed to evaluate condition event %s: %s", event_id, exc)
    if triggered_ids:
        interpreter.completed_events.update(triggered_ids)
    return triggered_actions, triggered_ids
