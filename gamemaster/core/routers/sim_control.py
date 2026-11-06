"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Simulator control endpoints and helpers for translating DSL actions.

The module normalizes trainer, DSL, and user inputs before queuing them
as simulator commands while sharing validation logic and schema loading.
"""

import json
import logging
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union, cast

from fastapi import APIRouter, HTTPException
from jsonschema import validate
from jsonschema import validate, ValidationError

from ..domain.controllers.global_instances import (
    get_control_value_resolver,
    get_event_store,
    get_simulation_controller,
    get_user_control_manager,
)
from ..entities.model import SimulationConfig, AggregateInput, AggregateOutput
from ..utils.clock import set_current_time, ClockRegressionError
from ..utils.schema_loader import load_simulation_config_schema
from ..services.value_cache import snapshot as value_snapshot
from ..utils.interval_scaling import apply_interval_law_scaling

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Simulator Control"])


class ControlValueType(str, Enum):
    """Describe how a control value should be interpreted."""

    DIRECT = "value"
    ABSOLUTE = "absolute"
    DELTA_PERCENT = "delta_percent"
    PERCENTAGE = "percentage"


@dataclass(frozen=True)
class ControlValue:
    """Represent a numeric control adjustment and its semantic meaning."""

    amount: float
    kind: ControlValueType


@dataclass(frozen=True)
class Control:
    """Normalized representation of a control command targeting a device."""

    control_type: str
    action: str
    target_id: str
    timestamp: Optional[float] = None
    attribute: Optional[str] = None
    setpoint: Optional[Dict[str, Any]] = None
    value: Optional[ControlValue] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """
        Convert the control into a dict payload suitable for APIs.

        Returns:
            Dict[str, Any]: Serialized representation excluding ``None``
            fields.
        """
        payload: Dict[str, Any] = {
            "control_type": self.control_type,
            "action": self.action,
            "id": self.target_id,
        }
        if self.timestamp is not None:
            payload["timestamp"] = self.timestamp
        if self.attribute is not None:
            payload["attribute"] = self.attribute
        if self.setpoint is not None:
            payload["setpoint"] = self.setpoint
        if self.value is not None:
            payload["value"] = self.value.amount
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload

    def with_default_timestamp(self, timestamp: float) -> "Control":
        """
        Return a copy with the timestamp filled in when missing.

        Args:
            timestamp (float): Default timestamp expressed in seconds.

        Returns:
            Control: Original control or cloned instance with timestamp.
        """
        if self.timestamp is not None:
            return self
        return replace(self, timestamp=timestamp)

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        """
        Safely coerce an arbitrary value to float.

        Args:
            value (Any): Value to convert.

        Returns:
            Optional[float]: Float when conversion succeeds, else None.
        """
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> Optional["Control"]:
        """
        Build a Control instance from an action-like payload.

        Args:
            payload (Dict[str, Any]): Raw dictionary describing a single
                control command.

        Returns:
            Optional[Control]: Control when the payload contains a target
            id; otherwise ``None``.
        """
        target = payload.get("id") or payload.get("target")
        if target is None:
            return None
        control_type = str(
            payload.get("control_type") or payload.get("element_type") or ""
        ).lower()
        action = str(payload.get("action") or payload.get("actionType") or "").lower()
        attribute = payload.get("attribute")
        timestamp = cls._coerce_float(payload.get("timestamp"))
        metadata = (
            payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        )
        value_obj = None
        value_raw = payload.get("value")
        coerced = cls._coerce_float(value_raw)
        if coerced is not None:
            value_obj = ControlValue(amount=coerced, kind=ControlValueType.DIRECT)
        return cls(
            control_type=control_type,
            action=action,
            target_id=str(target),
            timestamp=timestamp,
            attribute=attribute,
            setpoint=payload.get("setpoint"),
            value=value_obj,
            metadata=metadata,
        )

    @classmethod
    def from_components(
        cls,
        *,
        control_type: str,
        action: str,
        target_id: str,
        timestamp: Optional[float],
        attribute: Optional[str] = None,
        setpoint: Optional[Dict[str, Any]] = None,
        explicit_value: Any = None,
        fallback_percent: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Control":
        """
        Construct a Control from individual components used internally.

        Args:
            control_type (str): Element category being controlled.
            action (str): Operation to perform.
            target_id (str): Identifier of the target element.
            timestamp (Optional[float]): Absolute execution time.
            attribute (Optional[str]): Measurement attribute, if any.
            setpoint (Optional[Dict[str, Any]]): Structured setpoint data.
            explicit_value (Any): Direct numeric instruction, if provided.
            fallback_percent (Any): Value used when setpoints lack absolutes.
            metadata (Optional[Dict[str, Any]]): Additional context copied
                to the resulting control.

        Returns:
            Control: New control encapsulating the provided information.
        """
        resolved_attribute = attribute
        resolved_setpoint = setpoint if isinstance(setpoint, dict) else None
        value_obj: Optional[ControlValue] = None

        if resolved_attribute is None and resolved_setpoint:
            resolved_attribute = resolved_setpoint.get("attribute")

        explicit_numeric = cls._coerce_float(explicit_value)
        if explicit_numeric is not None:
            value_obj = ControlValue(
                amount=explicit_numeric, kind=ControlValueType.DIRECT
            )
        elif resolved_setpoint:
            absolute_value = cls._coerce_float(resolved_setpoint.get("absolute_value"))
            delta_percent = cls._coerce_float(resolved_setpoint.get("delta_percent"))
            if absolute_value is not None:
                value_obj = ControlValue(
                    amount=absolute_value, kind=ControlValueType.ABSOLUTE
                )
            elif delta_percent is not None:
                value_obj = ControlValue(
                    amount=delta_percent, kind=ControlValueType.DELTA_PERCENT
                )

        if value_obj is None:
            fallback_numeric = cls._coerce_float(fallback_percent)
            if fallback_numeric is not None:
                value_obj = ControlValue(
                    amount=fallback_numeric, kind=ControlValueType.PERCENTAGE
                )

        safe_metadata = metadata if isinstance(metadata, dict) else {}
        return cls(
            control_type=str(control_type or "").lower(),
            action=str(action or "").lower(),
            target_id=str(target_id),
            timestamp=timestamp,
            attribute=resolved_attribute,
            setpoint=resolved_setpoint,
            value=value_obj,
            metadata=safe_metadata,
        )


ControlLike = Union[Control, Dict[str, Any]]


def _ensure_control(candidate: ControlLike) -> Optional[Control]:
    """
    Convert a candidate object into a Control when possible.

    Args:
        candidate (ControlLike): Either a Control instance or dict.

    Returns:
        Optional[Control]: Parsed control or ``None`` when unsupported.
    """
    if isinstance(candidate, Control):
        return candidate
    if isinstance(candidate, dict):
        return Control.from_payload(candidate)
    return None


def _extract_percentage_hint(source: Optional[Dict[str, Any]]) -> Optional[float]:
    """
    Infer a percentage hint from DSL action payloads.

    Args:
        source (Optional[Dict[str, Any]]): Action dictionary.

    Returns:
        Optional[float]: First non-null percentage-like value found.
    """
    if not isinstance(source, dict):
        return None
    for key in ("percentage", "target_percentage"):
        value = Control._coerce_float(source.get(key))
        if value is not None:
            return value
    return None


def _recompute_absolute_values(action: dict) -> None:
    """
    Convert percentage-based setpoints into absolute values in-place.

    Args:
        action (dict): DSL action dictionary potentially containing
            ``setpoint`` or ``setpoints`` entries with percentage deltas.
    """
    if not isinstance(action, dict):
        return

    operation = str(action.get("operation") or "").lower()
    sign = -1.0 if operation == "decrease" else 1.0
    if not operation:
        event_type = str(action.get("type") or "").lower()
        if "decrease" in event_type:
            sign = -1.0
        elif "increase" in event_type:
            sign = 1.0

    def _update(entry: Optional[dict]) -> None:
        """
        Derive an absolute_value field for a single setpoint entry.

        Args:
            entry (Optional[dict]): Setpoint dictionary potentially
                containing ``basis_value`` and ``delta_percent``.
        """
        if not isinstance(entry, dict):
            return
        basis = entry.get("basis_value")
        delta = entry.get("delta_percent")
        try:
            basis_val = float(basis)
            delta_val = float(delta)
        except (TypeError, ValueError):
            return
        entry["absolute_value"] = basis_val * (1.0 + (delta_val / 100.0 * sign))

    _update(action.get("setpoint"))
    for sp in action.get("setpoints") or []:
        _update(sp)


def _store_event_to_action(evt: dict) -> dict:
    """
    Normalize a stored trainer event into an action dictionary.

    Args:
        evt (dict): Event-store row dictionary.

    Returns:
        dict: Action data capturing ids, targets, metadata, and payload.
    """
    typ = str(evt.get("type", "")).lower()
    target = evt.get("target")
    payload = evt.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    action = {"type": typ}
    scheduled_at = evt.get("at")
    if scheduled_at is None:
        scheduled_at = payload.get("t_start")
    if scheduled_at is None:
        scheduled_at = evt.get("interval_start")
    if evt.get("interval_start") is not None:
        action["interval_start"] = evt.get("interval_start")
    if evt.get("interval_end") is not None:
        action["interval_end"] = evt.get("interval_end")
    if typ == "invoke_function":
        for key in (
            "function_name",
            "bindings",
            "checked",
            "completion_event_id",
            "metadata",
        ):
            if key in payload:
                action[key] = payload[key]
    if typ == "change_network_characteristics":
        for key in (
            "links",
            "nodes",
            "delay_function",
            "drop_function",
            "corruption_functions",
            "t_start_from_now",
            "t_start",
            "metadata",
        ):
            if key in payload:
                action[key] = payload[key]
    elif typ == "print":
        if "message" in payload:
            action["message"] = payload["message"]
    if scheduled_at is not None and "t_start" not in action:
        try:
            action["t_start"] = float(scheduled_at)
        except (TypeError, ValueError):
            pass
    # Normalize element id(s)
    if isinstance(target, str):
        action["id"] = target
    elif target is not None:
        action["target"] = target
    targets = payload.get("targets")
    if targets is not None:
        action["targets"] = targets
        if "target" not in action:
            action["target"] = targets if isinstance(targets, list) else str(targets)

    if "percentage" in payload and payload["percentage"] is not None:
        action["percentage"] = payload["percentage"]
    if "target_percentage" in payload and payload["target_percentage"] is not None:
        action["target_percentage"] = payload["target_percentage"]
    if payload.get("attribute"):
        action["attribute"] = payload["attribute"]
    if payload.get("operation"):
        action["operation"] = payload["operation"]
    if payload.get("element_type"):
        action["element_type"] = payload["element_type"]
    if payload.get("setpoint"):
        action["setpoint"] = payload["setpoint"]
    if payload.get("setpoints"):
        action["setpoints"] = payload["setpoints"]
    if payload.get("measurement_keys"):
        action["measurement_keys"] = payload["measurement_keys"]
    if payload.get("target_spec"):
        action["target_spec"] = payload["target_spec"]

    event_id = evt.get("id")
    metadata = {}
    if isinstance(evt.get("metadata"), dict):
        metadata.update(evt["metadata"])
    if isinstance(action.get("metadata"), dict):
        metadata.update(action["metadata"])
    if event_id:
        metadata = dict(metadata)
        metadata["event_id"] = event_id
    time_spec = evt.get("time_spec")
    if time_spec is not None:
        metadata = dict(metadata)
        metadata["time_spec"] = str(time_spec).lower()
    interval_end = evt.get("interval_end")
    if interval_end is not None:
        metadata = dict(metadata)
        metadata["interval_end"] = interval_end
    source = evt.get("source")
    if source is not None:
        metadata = dict(metadata)
        metadata["source"] = str(source).lower()
    if metadata:
        action["metadata"] = metadata
    return action


def _expand_store_invoke_function_event(
    evt: dict,
    interpreter,
    *,
    current_time: float,
    system_state: dict,
) -> tuple[list[dict], set[str], float]:
    """Expand a persisted invoke_function event into immediate child actions."""
    action_dict = _store_event_to_action(evt)
    invocation_time = evt.get("at")
    if invocation_time is None:
        invocation_time = action_dict.get("t_start")
    if invocation_time is None:
        lead = getattr(interpreter, "time_step", None)
        try:
            lead = float(lead) if lead is not None else 0.0
        except (TypeError, ValueError):
            lead = 0.0
        invocation_time = float(current_time) + lead
    else:
        invocation_time = float(invocation_time)

    original_source = getattr(interpreter, "event_source", None)
    try:
        interpreter.event_source = str(evt.get("source") or original_source or "dsl")
        expansion = interpreter._invoke_function_action(
            action_dict,
            invocation_time=invocation_time,
            system_state=system_state,
        )
    finally:
        interpreter.event_source = original_source

    completed_ids: set[str] = set()
    event_id = evt.get("id")
    if event_id:
        completed_ids.add(str(event_id))
    for completion_id in expansion.get("completed_ids", []) or []:
        if completion_id:
            completed_ids.add(str(completion_id))
    return list(expansion.get("actions") or []), completed_ids, invocation_time


def _point_event_ids_from_actions(actions: Sequence[dict]) -> set[str]:
    """Collect point-event ids from immediate expanded actions."""
    event_ids: set[str] = set()
    for item in actions:
        if isinstance(item, dict) and "action" in item:
            continue
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        event_id = metadata.get("event_id")
        time_spec = str(metadata.get("time_spec") or "").lower()
        if event_id and (not time_spec or time_spec == "point"):
            event_ids.add(str(event_id))
    return event_ids


def _trainer_event_to_controls(
    evt: dict, prepared_action: dict, *, timestamp: Optional[float]
) -> List[Control]:
    """
    Expand a trainer DSL event into per-target Control objects.

    Args:
        evt (dict): Raw event-store record.
        prepared_action (dict): Normalized action derived from the event.
        timestamp (Optional[float]): Execution time assigned to controls.

    Returns:
        List[Control]: Collection of controls for each resolved target.
    """
    event_type = str(prepared_action.get("type") or evt.get("type") or "")
    action = str(prepared_action.get("operation") or "")
    control_type = str(prepared_action.get("element_type") or "")
    if "_" in event_type:
        prefix, suffix = event_type.split("_", 1)
        if not action:
            action = prefix
        if not control_type:
            control_type = suffix

    action = action.lower()
    control_type = control_type.lower()

    targets = prepared_action.get("targets")
    if isinstance(targets, str):
        targets = [targets]
    targets = [str(t) for t in (targets or []) if t is not None]
    if not targets:
        single_target = prepared_action.get("target")
        if single_target is not None:
            targets = [str(single_target)]
    if not targets:
        identifier = prepared_action.get("id")
        if identifier is not None:
            targets = [str(identifier)]
    if not targets:
        return []

    setpoint_entries = prepared_action.get("setpoints") or []
    per_target_setpoints = {
        str(entry.get("id")): entry
        for entry in setpoint_entries
        if entry.get("id") is not None
    }

    attribute = prepared_action.get("attribute")
    controls: List[Control] = []
    default_setpoint = prepared_action.get("setpoint")
    fallback_percent = _extract_percentage_hint(prepared_action)
    metadata = (
        prepared_action.get("metadata")
        if isinstance(prepared_action.get("metadata"), dict)
        else {}
    )
    event_metadata = (
        evt.get("metadata") if isinstance(evt.get("metadata"), dict) else {}
    )
    merged_metadata = dict(metadata)
    merged_metadata.update(event_metadata)
    event_id = evt.get("id")
    if event_id:
        merged_metadata["event_id"] = event_id
    time_spec = evt.get("time_spec")
    if time_spec is not None:
        merged_metadata["time_spec"] = str(time_spec).lower()
    source = evt.get("source")
    if source is not None:
        merged_metadata["source"] = str(source).lower()
    for target in targets:
        setpoint = per_target_setpoints.get(target) or default_setpoint
        per_target_metadata = dict(merged_metadata)
        ctrl = Control.from_components(
            control_type=control_type,
            action=action,
            target_id=target,
            timestamp=timestamp,
            attribute=attribute,
            setpoint=setpoint,
            fallback_percent=fallback_percent,
            metadata=per_target_metadata,
        )
        controls.append(ctrl)
    return controls


def _raw_event_to_control(evt: dict) -> List[Control]:
    """
    Translate a generic event-store record into control objects.

    Args:
        evt (dict): Event-store row representing either DSL or user data.

    Returns:
        List[Control]: Controls derived from the payload.
    """
    event_type = str(evt.get("type", "") or "")
    if "_" in event_type:
        action, control_type = event_type.split("_", 1)
    else:
        action = event_type
        control_type = str(evt.get("control_type", ""))

    control_type = control_type.lower()
    action = action.lower()
    timestamp = evt.get("due_at") or evt.get("at") or evt.get("interval_start")
    try:
        timestamp = float(timestamp)
    except (TypeError, ValueError):
        timestamp = None

    raw_target = evt.get("target")
    targets: List[str] = []
    if isinstance(raw_target, list):
        targets = [str(t) for t in raw_target if t is not None]
    elif raw_target is not None:
        targets = [str(raw_target)]
    if not targets:
        identifier = evt.get("id")
        if identifier is not None:
            targets = [str(identifier)]
    if not targets:
        return []

    payload = evt.get("payload") or {}
    metadata = evt.get("metadata") if isinstance(evt.get("metadata"), dict) else {}
    event_metadata = dict(metadata) if metadata else {}
    event_id = evt.get("id")
    if event_id:
        event_metadata["event_id"] = event_id
    time_spec = evt.get("time_spec")
    if time_spec is not None:
        event_metadata["time_spec"] = str(time_spec).lower()
    source = evt.get("source")
    if source is not None:
        event_metadata["source"] = str(source).lower()
    controls: List[Control] = []
    per_target_setpoints = {}
    setpoints = payload.get("setpoints") or []
    for sp in setpoints:
        ident = sp.get("id")
        if ident is not None:
            per_target_setpoints[str(ident)] = sp
    fallback_percent = payload.get("target_percentage")
    if fallback_percent is None:
        fallback_percent = payload.get("percentage")
    attribute = payload.get("attribute")
    default_setpoint = payload.get("setpoint")
    explicit_value = payload.get("value")
    for target in targets:
        matching_setpoint = per_target_setpoints.get(target) or default_setpoint
        per_target_metadata = dict(event_metadata)
        ctrl = Control.from_components(
            control_type=control_type,
            action=action,
            target_id=target,
            timestamp=timestamp,
            attribute=attribute,
            setpoint=matching_setpoint,
            explicit_value=explicit_value,
            fallback_percent=fallback_percent,
            metadata=per_target_metadata,
        )
        controls.append(ctrl)
    return controls


def transform_dsl_action(raw_action: dict, step: float) -> dict:
    """Normalize a DSL action (point or interval) into the AggregateOutput shape."""

    interval_info = None
    action = raw_action

    if isinstance(raw_action, dict) and "action" in raw_action:
        interval_info = {
            "start": raw_action.get("interval_start", step),
            "end": raw_action.get("interval_end", step),
            "law": raw_action.get("law"),
        }
        action = raw_action.get("action")

    if not isinstance(action, dict):
        return {
            "timestamp": step,
            "actionType": str(action),
            "details": {},
        }

    typ = action.get("type", "")
    if typ == "change_network_characteristics":
        network_details = {
            "elementId": "network",
            "links": action.get("links", []),
            "nodes": action.get("nodes", []),
        }
        if action.get("delay_function") is not None:
            network_details["delay_function"] = action.get("delay_function")
        if action.get("drop_function") is not None:
            network_details["drop_function"] = action.get("drop_function")
        if action.get("corruption_functions") is not None:
            network_details["corruption_functions"] = action.get("corruption_functions")

        transformed = {
            "timestamp": step,
            "actionType": "change_network_characteristics",
            "details": network_details,
        }
        if interval_info:
            transformed["interval_start"] = interval_info.get("start")
            transformed["interval_end"] = interval_info.get("end")
            transformed["law"] = interval_info.get("law")
        if "metadata" in action:
            transformed["metadata"] = action["metadata"]
        return transformed

    if typ == "print":
        transformed = {
            "timestamp": step,
            "actionType": "print",
            "details": {"message": action.get("message", "")},
        }
        if interval_info:
            transformed["interval_start"] = interval_info.get("start")
            transformed["interval_end"] = interval_info.get("end")
            transformed["law"] = interval_info.get("law")
        if "metadata" in action:
            transformed["metadata"] = action["metadata"]
        return transformed

    is_fault = "fault" in typ
    action_type = typ if is_fault else typ.split("_")[0] if typ else ""

    details: dict = {}
    if is_fault:
        details = {
            "component_type": action.get("component_type", "line"),
            "id": action.get("id"),
        }
    else:
        details = {"elementId": action.get("id") or action.get("target")}
        if "load" in typ or "generator" in typ:
            details["percentage"] = action.get("percentage")
            setpoint = action.get("setpoint") or {}
            if setpoint.get("attribute"):
                details["attribute"] = setpoint.get("attribute")
            if setpoint.get("absolute_value") is not None:
                details["absoluteValue"] = setpoint.get("absolute_value")
            elif setpoint.get("absolute_values"):
                details["absoluteValues"] = setpoint.get("absolute_values")
            if action.get("targets"):
                details["targets"] = action.get("targets")

    transformed_action = {
        "timestamp": step,
        "actionType": action_type,
        "details": details,
    }

    if interval_info:
        transformed_action["interval_start"] = interval_info.get("start")
        transformed_action["interval_end"] = interval_info.get("end")
        transformed_action["law"] = interval_info.get("law")

    if "metadata" in action:
        transformed_action["metadata"] = action["metadata"]

    return transformed_action


def transform_control_action(ctrl: ControlLike) -> dict:
    """Convert a control payload into the AggregateOutput action shape."""

    if isinstance(ctrl, Control):
        timestamp = ctrl.timestamp
        action_type = ctrl.action
        control_type = ctrl.control_type
        element_id = ctrl.target_id
        setpoint = ctrl.setpoint or {}
        value = ctrl.value.amount if ctrl.value else None
        attribute = ctrl.attribute
        raw_details = None
    else:
        payload = ctrl
        timestamp = payload.get("timestamp")
        action_type = str(payload.get("action", ""))
        control_type = str(payload.get("control_type", "")).lower()
        element_id = payload.get("id")
        setpoint = payload.get("setpoint") or {}
        value = payload.get("value")
        attribute = payload.get("attribute")
        raw_details = payload

    if control_type == "switch":
        details = {"elementId": str(element_id)}
    elif control_type in {"load", "generator"}:
        details = {
            "elementId": str(element_id),
        }
        if value is not None:
            details["percentage"] = value
        if setpoint.get("absolute_value") is not None:
            details["absoluteValue"] = setpoint.get("absolute_value")
        if setpoint.get("attribute"):
            details["attribute"] = setpoint.get("attribute")
        elif attribute:
            details["attribute"] = attribute
    else:
        details = dict(raw_details) if raw_details is not None else ctrl.to_payload()  # type: ignore[union-attr]

    return {
        "timestamp": timestamp,
        "actionType": action_type,
        "details": details,
    }


def _with_default_timestamp(ctrl: ControlLike, timestamp: float) -> Control:
    """
    Ensure a control has a timestamp, defaulting when absent.

    Args:
        ctrl (ControlLike): Control or payload to normalize.
        timestamp (float): Timestamp applied when missing.

    Returns:
        Control: Control instance guaranteed to include a timestamp.

    Raises:
        ValueError: If the payload cannot be converted into a control.
    """
    control = _ensure_control(ctrl)
    if control is None:
        raise ValueError("Control payload missing id/structure")
    return control.with_default_timestamp(timestamp)


def _controls_to_actions(controls: Sequence[ControlLike]) -> List[dict]:
    """
    Convert a sequence of controls into AggregateOutput actions.

    Args:
        controls (Sequence[ControlLike]): Controls or payloads.

    Returns:
        List[dict]: Action dictionaries.
    """
    return [transform_control_action(ctrl) for ctrl in controls]


def _resolve_numeric_value(control_type: str, action: str) -> Optional[float]:
    """
    Look up the numeric representation for a control/action pair.

    Args:
        control_type (str): Control category.
        action (str): Operation name.

    Returns:
        Optional[float]: Numeric value from ControlValueResolver.
    """
    resolver = get_control_value_resolver()
    return resolver.resolve(control_type, action)


def _collect_dsl_actions(simulation_controller, current_time: float) -> List[dict]:
    """
    Fetch DSL actions scheduled for the current simulation step.

    Args:
        simulation_controller: SimulationController providing the DSL
            interpreter.
        current_time (float): Timestamp used when normalizing interval
            bounds.

    Returns:
        List[dict]: Actions transformed via `transform_dsl_action`.
    """
    system_state = value_snapshot()
    step_data = simulation_controller.get_next_step(current_time, system_state)
    raw_actions = step_data.get("actions", []) if isinstance(step_data, dict) else []
    logger.debug("Raw DSL actions from get_next_step: %s", raw_actions)
    default_interval_end = current_time + 1
    normalized: List[dict] = []
    for action in raw_actions:
        if isinstance(action, dict) and "action" in action:
            container = dict(action)
            container.setdefault("interval_start", current_time)
            container.setdefault("interval_end", default_interval_end)
            normalized.append(transform_dsl_action(container, current_time))
        else:
            normalized.append(transform_dsl_action(action, current_time))
    return normalized


def _collect_user_controls(current_time: float) -> List[Control]:
    """
    Retrieve user-submitted controls due at `current_time`.

    Args:
        current_time (float): Timestamp forwarded to the user manager.

    Returns:
        List[Control]: Timestamp-normalized controls.
    """
    manager = get_user_control_manager()
    raw_controls = manager.get_controls_for_step(current_time)
    logger.debug("Raw user controls: %s", raw_controls)
    normalized: List[Control] = []
    for payload in raw_controls:
        ctrl = Control.from_payload(payload)
        if ctrl is None:
            continue
        normalized.append(ctrl.with_default_timestamp(current_time))
    return normalized


def _collect_trainer_controls(
    simulation_controller, current_time: float
) -> List[Control]:
    """
    Fetch trainer-originated events that align with `current_time`.

    Args:
        simulation_controller: SimulationController referencing the
            interpreter and simulation metadata.
        current_time (float): Timestamp used to query due events.

    Returns:
        List[Control]: Controls derived from due trainer events.
    """
    event_store = get_event_store()
    interpreter = simulation_controller.interpreter
    if interpreter is None:
        return []
    eps = max(1e-3, (interpreter.time_step or 0) / 10.0)

    try:
        due = event_store.events_due(
            current_time,
            eps,
            simulation=simulation_controller.simulation_name,
        )
    except Exception as exc:
        logger.warning(
            "Failed to fetch trainer events at time %s: %s", current_time, exc
        )
        return []

    point_ids: set[str] = set()
    controls: List[Control] = []
    system_state = value_snapshot()

    for evt in due.get("points", []):
        if str(evt.get("source", "")).lower() != "trainer":
            continue
        action_dict = _store_event_to_action(evt)
        if str(action_dict.get("type") or "").lower() == "invoke_function":
            expanded_actions, completion_ids, invocation_time = _expand_store_invoke_function_event(
                evt,
                interpreter,
                current_time=current_time,
                system_state=system_state,
            )
            point_ids.update(completion_ids)
            point_ids.update(_point_event_ids_from_actions(expanded_actions))
            for item in expanded_actions:
                prepared_action = item.get("action") if isinstance(item, dict) and "action" in item else item
                if not isinstance(prepared_action, dict):
                    continue
                fake_evt = {
                    "id": (prepared_action.get("metadata") or {}).get("event_id"),
                    "source": evt.get("source"),
                    "time_spec": "interval" if isinstance(item, dict) and "action" in item else "point",
                    "metadata": prepared_action.get("metadata"),
                }
                ctrls = _trainer_event_to_controls(
                    fake_evt,
                    prepared_action,
                    timestamp=invocation_time,
                )
                if ctrls:
                    controls.extend(ctrls)
            continue
        prepared_action = interpreter.prepare_action(action_dict, system_state)
        timestamp = evt.get("at")
        try:
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            timestamp = None
        ctrls = _trainer_event_to_controls(evt, prepared_action, timestamp=timestamp)
        if not ctrls:
            continue
        controls.extend(ctrls)
        if evt.get("id"):
            point_ids.add(str(evt.get("id")))

    for evt in due.get("intervals", []):
        if str(evt.get("source", "")).lower() != "trainer":
            continue
        action_dict = _store_event_to_action(evt)
        prepared_action = interpreter.prepare_action(action_dict, system_state)
        lead = getattr(interpreter, "time_step", None)
        try:
            lead = float(lead) if lead is not None else 0.0
        except (TypeError, ValueError):
            lead = 0.0
        timestamp = current_time + lead
        ctrls = _trainer_event_to_controls(evt, prepared_action, timestamp=timestamp)
        if ctrls:
            controls.extend(ctrls)

    if point_ids:
        try:
            event_store.mark_completed(list(point_ids))
        except Exception as exc:
            logger.warning("Failed to mark trainer events completed: %s", exc)

    return [
        cast(Control, _with_default_timestamp(ctrl, current_time)) for ctrl in controls
    ]


def _partition_due_events(due: dict, current_time: float):
    """
    Separate due events into raw actions, user controls, and trainer controls.

    Args:
        due (dict): Structure returned by `EventStore.events_due`.
        current_time (float): Timestamp used when normalizing controls.

    Returns:
        tuple: `(raw_actions, user_controls, trainer_controls, point_ids, completion_ids)`
        where each collection contains normalized data structures.
    """
    raw_actions: List[dict] = []
    user_controls: List[Control] = []
    trainer_controls: List[Control] = []
    point_ids: List[str] = []
    completion_ids: set[str] = set()
    simulation_controller = get_simulation_controller()
    interpreter = simulation_controller.interpreter if simulation_controller else None
    system_state = value_snapshot() if interpreter else {}

    for evt in due.get("points", []):
        src = str(evt.get("source", "")).lower()
        action_dict = _store_event_to_action(evt)
        if (
            interpreter
            and str(action_dict.get("type") or "").lower() == "invoke_function"
        ):
            expanded_actions, expanded_completion_ids, invocation_time = _expand_store_invoke_function_event(
                evt,
                interpreter,
                current_time=current_time,
                system_state=system_state,
            )
            completion_ids.update(expanded_completion_ids)
            if src == "trainer":
                for item in expanded_actions:
                    prepared_action = item.get("action") if isinstance(item, dict) and "action" in item else item
                    if not isinstance(prepared_action, dict):
                        continue
                    action_type = str(prepared_action.get("type") or "").lower()
                    if action_type == "change_network_characteristics":
                        raw_actions.append(item if isinstance(item, dict) and "action" in item else prepared_action)
                        continue
                    fake_evt = {
                        "id": (prepared_action.get("metadata") or {}).get("event_id"),
                        "source": evt.get("source"),
                        "time_spec": "interval" if isinstance(item, dict) and "action" in item else "point",
                        "metadata": prepared_action.get("metadata"),
                    }
                    ctrls = _trainer_event_to_controls(
                        fake_evt,
                        prepared_action,
                        timestamp=invocation_time,
                    )
                    if ctrls:
                        trainer_controls.extend(
                            cast(Control, _with_default_timestamp(c, current_time))
                            for c in ctrls
                        )
                continue
            raw_actions.extend(expanded_actions)
            continue
        if src == "user":
            ctrl = _raw_event_to_control(evt)
            if ctrl:
                user_controls.extend(
                    cast(Control, _with_default_timestamp(c, current_time))
                    for c in ctrl
                )
                point_ids.append(evt.get("id"))
            continue
        if src == "trainer":
            if interpreter:
                prepared_action = interpreter.prepare_action(action_dict, system_state)
                action_type = str(prepared_action.get("type") or "").lower()
                if action_type in {"change_network_characteristics", "print"}:
                    raw_actions.append(prepared_action)
                    point_ids.append(evt.get("id"))
                    continue
                timestamp = evt.get("at")
                try:
                    timestamp = float(timestamp)
                except (TypeError, ValueError):
                    timestamp = None
                ctrl = _trainer_event_to_controls(
                    evt, prepared_action, timestamp=timestamp
                )
            else:
                ctrl = _raw_event_to_control(evt)
            if ctrl:
                trainer_controls.extend(
                    cast(Control, _with_default_timestamp(c, current_time))
                    for c in ctrl
                )
                point_ids.append(evt.get("id"))
            continue
        raw_actions.append(action_dict)
        point_ids.append(evt.get("id"))

    for evt in due.get("intervals", []):
        src = str(evt.get("source", "")).lower()
        if src == "user":
            ctrl = _raw_event_to_control(evt)
            if ctrl:
                user_controls.extend(
                    cast(Control, _with_default_timestamp(c, current_time))
                    for c in ctrl
                )
            continue
        if src == "trainer":
            if interpreter:
                action_dict = _store_event_to_action(evt)
                prepared_action = interpreter.prepare_action(action_dict, system_state)
                original_percentage = prepared_action.get("percentage")
                action_type = str(prepared_action.get("type") or "").lower()
                if action_type in {"change_network_characteristics", "print"}:
                    raw_actions.append(
                        {
                            "action": prepared_action,
                            "interval_start": evt.get("interval_start"),
                            "interval_end": evt.get("interval_end"),
                            "law": evt.get("law"),
                        }
                    )
                    continue
                container = {
                    "action": prepared_action,
                    "interval_start": evt.get("interval_start"),
                    "interval_end": evt.get("interval_end"),
                    "law": evt.get("law"),
                }
                apply_interval_law_scaling(
                    container, current_time, getattr(interpreter, "time_step", None)
                )
                if prepared_action.get("percentage") != original_percentage:
                    _recompute_absolute_values(prepared_action)
                lead = getattr(interpreter, "time_step", None)
                try:
                    lead = float(lead) if lead is not None else 0.0
                except (TypeError, ValueError):
                    lead = 0.0
                timestamp = current_time + lead
                ctrl = _trainer_event_to_controls(
                    evt, prepared_action, timestamp=timestamp
                )
            else:
                ctrl = _raw_event_to_control(evt)
            if ctrl:
                trainer_controls.extend(
                    cast(Control, _with_default_timestamp(c, current_time))
                    for c in ctrl
                )
            continue
        act = _store_event_to_action(evt)
        raw_actions.append(
            {
                "action": act,
                "interval_start": evt.get("interval_start"),
                "interval_end": evt.get("interval_end"),
                "law": evt.get("law"),
            }
        )

    return raw_actions, user_controls, trainer_controls, point_ids, completion_ids


def _ensure_interpreter(simulation_controller):
    """
    Ensure the simulation controller has an active interpreter.

    Args:
        simulation_controller: SimulationController instance.

    Returns:
        DSL interpreter associated with the controller.

    Raises:
        HTTPException: If the interpreter has not been initialized.
    """
    interpreter = simulation_controller.interpreter
    if interpreter is None:
        raise HTTPException(status_code=400, detail="Simulation not initialized.")
    return interpreter


def _build_simulation_config(
    simulation_controller, actions: List[dict], current_time: float
) -> SimulationConfig:
    """
    Assemble and validate the AggregateOutput payload returned to clients.

    Args:
        simulation_controller: Controller providing interpreter metadata.
        actions (List[dict]): Actions scheduled for the current step.
        current_time (float): Simulation timestamp included in response.

    Returns:
        SimulationConfig: Pydantic model containing the aggregated state.
    """
    interpreter = _ensure_interpreter(simulation_controller)
    sim_config_dict = {
        "simulationName": simulation_controller.simulation_name,
        "startTime": 0,
        "endTime": interpreter.duration,
        "timeStep": interpreter.time_step,
        "currentStep": current_time,
        "actions": actions,
    }

    validate(instance=sim_config_dict, schema=load_simulation_config_schema())
    validate(instance=sim_config_dict, schema=load_simulation_config_schema())
    logger.debug("Simulation config for response: %s", sim_config_dict)
    return SimulationConfig(**sim_config_dict)


def _action_conflict_keys(action: dict) -> List[tuple]:
    """
    Generate keys used to deduplicate conflicting actions.

    Args:
        action (dict): AggregateOutput action structure.

    Returns:
        List[tuple]: One or more tuples combining target, action type, and
        timestamp used when merging priorities.
    """
    details = action.get("details") or {}
    action_type = action.get("actionType")
    targets = None
    if "elementId" in details and details["elementId"] is not None:
        targets = details["elementId"]
    elif "id" in details and details["id"] is not None:
        ident = details["id"]
        comp = details.get("component_type")
        targets = f"{comp}:{ident}" if comp else ident
    elif "target" in details and details["target"] is not None:
        targets = details["target"]

    if action_type == "print":
        metadata = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
        event_id = metadata.get("event_id")
        message = details.get("message")
        normalized = [f"print:{event_id if event_id is not None else message}"]
    elif isinstance(targets, list):
        normalized = [str(t) for t in targets]
    elif targets is None:
        normalized = [f"__{action_type}__"]
    else:
        normalized = [str(targets)]

    timestamp = action.get("timestamp") or action.get("interval_start")
    return [(t, action_type, timestamp) for t in normalized]


def _merge_actions_by_priority(*groups: List[dict]) -> List[dict]:
    """
    Merge multiple action lists while discarding conflicts encountered earlier.

    Args:
        *groups (List[dict]): Ordered action groups, typically DSL,
            trainer, and user actions.

    Returns:
        List[dict]: Combined list preserving the first occurrence of each
        conflict group.
    """
    seen = {}
    merged: List[dict] = []
    for actions in groups:
        for action in actions:
            keys = _action_conflict_keys(action)
            if any(key in seen for key in keys):
                continue
            for key in keys:
                seen[key] = action
            merged.append(action)
    return merged


@router.post("/simulatorcontrol", response_model=AggregateOutput)
def simulator_control(input_data: AggregateInput):
    """
    Aggregate DSL, trainer, and user actions for the next simulation step.

    Args:
        input_data (AggregateInput): Request payload containing the
            current simulation time.

    Returns:
        SimulationConfig: Combined action snapshot serialized by FastAPI.

    Raises:
        HTTPException: When validation fails or processing encounters an
        unexpected error.
    """
    try:
        current_time = input_data.current_time
        logger.debug("Processing simulatorcontrol for time: %s", current_time)

        simulation_controller = get_simulation_controller()
        dsl_actions = _collect_dsl_actions(simulation_controller, current_time)

        user_controls = _collect_user_controls(current_time)
        user_actions = _controls_to_actions(user_controls)

        trainer_controls = _collect_trainer_controls(
            simulation_controller, current_time
        )
        trainer_actions = _controls_to_actions(trainer_controls)
        logger.debug("Trainer actions: %s", trainer_actions)

        aggregated_actions = _merge_actions_by_priority(
            dsl_actions,
            trainer_actions,
            user_actions,
        )
        logger.debug("Aggregated actions after priority merge: %s", aggregated_actions)

        return _build_simulation_config(
            simulation_controller, aggregated_actions, current_time
        )
    except ValidationError as ve:
        logger.error("Schema validation error: %s", ve.message)
        raise HTTPException(
            status_code=422, detail=f"Schema validation error: {ve.message}"
        )
    except Exception as e:
        logger.error("Error in simulator_control: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _control_to_v2_command(ctrl: Control) -> Optional[dict]:
    """
    Convert a Control into the v2 IIDM command schema.

    Args:
        ctrl (Control): Normalized control to translate.

    Returns:
        Optional[dict]: Command payload or ``None`` when the control
        cannot be expressed in the v2 schema.
    """
    if not ctrl.target_id:
        return None

    control_type = ctrl.control_type
    action = ctrl.action
    target_id = ctrl.target_id

    if control_type == "switch":
        value = _resolve_numeric_value(control_type, action)
        if value is None:
            logger.debug("Skipping switch control without numeric mapping: %s", ctrl)
            return None
        attribute = "state"
        element_type = "switch"
    elif control_type == "line":
        value = _resolve_numeric_value(control_type, action)
        if value is None:
            logger.debug("Skipping line control without numeric mapping: %s", ctrl)
            return None
        attribute = "state"
        element_type = "line"
    elif control_type in ("load", "generator") and action in (
        "increase",
        "decrease",
        "set",
    ):
        setpoint = ctrl.setpoint or {}
        attribute = (setpoint.get("attribute") or ctrl.attribute or "P").upper()
        absolute_value = setpoint.get("absolute_value")
        if absolute_value is None:
            val = ctrl.value.amount if ctrl.value else None
            if val is None:
                return None
            try:
                numeric = float(val)
            except (TypeError, ValueError):
                return None
            if action == "set":
                value = numeric
            else:
                value = numeric if action == "increase" else -numeric
        else:
            try:
                value = float(absolute_value)
            except (TypeError, ValueError):
                return None
        element_type = control_type
    else:
        return None

    cmd = {
        "command": "iidm_command",
        "iidm_id": target_id,
        "attribute": attribute,
        "element_type": element_type,
        "value": value,
    }
    if ctrl.timestamp is not None:
        try:
            cmd["t_start"] = float(ctrl.timestamp)
        except (TypeError, ValueError):
            pass
    metadata = ctrl.metadata if isinstance(ctrl.metadata, dict) else {}
    if metadata:
        cmd["metadata"] = metadata
    return cmd


def _command_conflict_keys(cmd: dict) -> tuple:
    """
    Produce a canonical key for deduplicating IIDM commands.

    Args:
        cmd (dict): Command candidate.

    Returns:
        tuple: Tuple representing uniqueness for the command.
    """
    command_name = cmd.get("command")
    if command_name == "change_network_characteristics":
        canonical = {
            "links": cmd.get("links"),
            "nodes": cmd.get("nodes"),
            "delay_function": cmd.get("delay_function"),
            "drop_function": cmd.get("drop_function"),
            "corruption_functions": cmd.get("corruption_functions"),
            "t_start": cmd.get("t_start"),
            "metadata": cmd.get("metadata"),
        }
        return (command_name, json.dumps(canonical, sort_keys=True, default=str))
    if command_name == "print":
        metadata = cmd.get("metadata") if isinstance(cmd.get("metadata"), dict) else {}
        return (
            command_name,
            metadata.get("event_id") or cmd.get("message"),
            cmd.get("t_start"),
        )
    return (cmd.get("iidm_id"), cmd.get("attribute"), command_name, cmd.get("t_start"))


def _merge_commands_by_priority(*groups: List[dict]) -> List[dict]:
    """
    Merge command groups while preserving the first occurrence per conflict key.

    Args:
        *groups (List[dict]): Ordered iterables of commands.

    Returns:
        List[dict]: Combined command list.
    """
    seen = set()
    merged: List[dict] = []
    for commands in groups:
        for cmd in commands:
            key = _command_conflict_keys(cmd)
            if key in seen:
                continue
            seen.add(key)
            merged.append(cmd)
    return merged


def _strip_command_metadata(commands: List[dict]) -> List[dict]:
    """
    Remove metadata from commands before returning them to clients.

    Args:
        commands (List[dict]): Command payloads.

    Returns:
        List[dict]: Commands without ``metadata`` keys.
    """
    sanitized: List[dict] = []
    for cmd in commands:
        if isinstance(cmd, dict) and "metadata" in cmd:
            sanitized.append({k: v for k, v in cmd.items() if k != "metadata"})
        else:
            sanitized.append(cmd)
    return sanitized


def _command_event_ids(
    commands: Sequence[dict], *, current_time: float | None = None
) -> set[str]:
    """
    Collect event ids safe to mark as completed.

    Args:
        commands (Sequence[dict]): Commands produced for simulatorcontrol_v2.
        current_time (Optional[float]): Current simulation time used to
            recognize interval commands that reached their final tick.

    Returns:
        set[str]: Event identifiers safe to mark as completed.
    """
    event_ids: set[str] = set()
    for cmd in commands:
        if not isinstance(cmd, dict):
            continue
        command_name = str(cmd.get("command") or "").lower()
        if command_name not in {"change_network_characteristics", "iidm_command", "print"}:
            continue
        metadata = cmd.get("metadata") if isinstance(cmd.get("metadata"), dict) else {}
        event_id = metadata.get("event_id")
        time_spec = str(metadata.get("time_spec") or "").lower()
        if time_spec == "interval":
            interval_end = metadata.get("interval_end")
            try:
                if (
                    current_time is None
                    or interval_end is None
                    or float(current_time) + 1e-9 < float(interval_end)
                ):
                    continue
            except (TypeError, ValueError):
                continue
        elif time_spec and time_spec != "point":
            continue
        if event_id:
            event_ids.add(str(event_id))
    return event_ids


def _to_v2_commands_from_inputs(
    raw_dsl_actions,
    raw_trainer_controls,
    raw_user_controls,
    *,
    default_start_time=None,
    interval_lead=None,
    current_time=None,
):
    """
    Convert heterogeneous raw inputs into v2 IIDM commands.

    Args:
        raw_dsl_actions: Actions parsed from DSL events.
        raw_trainer_controls: Trainer-derived Control objects.
        raw_user_controls: User Control objects.

    Returns:
        List[dict]: Deduplicated IIDM commands ready for response.
    """
    dsl_cmds: List[dict] = []
    for a in raw_dsl_actions:
        try:
            action = a.get("action", a)
            metadata = (
                action.get("metadata")
                if isinstance(action.get("metadata"), dict)
                else {}
            )
            is_interval = isinstance(a, dict) and (
                "interval_start" in a or "interval_end" in a
            )
            typ = str(action.get("type", "")).lower()
            if typ == "change_network_characteristics":
                cmd = {
                    "command": "change_network_characteristics",
                    "links": action.get("links", []),
                    "nodes": action.get("nodes", []),
                }

                if action.get("metadata") is not None:
                    cmd["metadata"] = action.get("metadata")
                if is_interval:
                    start_at = action.get("interval_start", default_start_time)
                    if current_time is not None and interval_lead is not None:
                        try:
                            start_at = float(current_time) + float(interval_lead)
                        except (TypeError, ValueError):
                            pass
                else:
                    start_at = action.get("t_start", default_start_time)
                if start_at is not None:
                    try:
                        cmd["t_start"] = float(start_at)
                    except (TypeError, ValueError):
                        pass
                if action.get("delay_function") is not None:
                    cmd["delay_function"] = action.get("delay_function")
                if action.get("drop_function") is not None:
                    cmd["drop_function"] = action.get("drop_function")
                if action.get("corruption_functions") is not None:
                    cmd["corruption_functions"] = action.get("corruption_functions")
                dsl_cmds.append(cmd)
                continue
            if typ == "print":
                cmd = {
                    "command": "print",
                    "message": action.get("message", ""),
                }
                if action.get("metadata") is not None:
                    cmd["metadata"] = action.get("metadata")
                if is_interval:
                    start_at = action.get("interval_start", default_start_time)
                    if current_time is not None and interval_lead is not None:
                        try:
                            start_at = float(current_time) + float(interval_lead)
                        except (TypeError, ValueError):
                            pass
                else:
                    start_at = action.get("t_start", default_start_time)
                if start_at is not None:
                    try:
                        cmd["t_start"] = float(start_at)
                    except (TypeError, ValueError):
                        pass
                dsl_cmds.append(cmd)
                continue
            if "fault" in typ:
                continue
            if "switch" in typ:
                element_type = "switch"
                op = "close" if "close" in typ else ("open" if "open" in typ else None)
                if op is None:
                    continue
                attribute = "state"
                value = _resolve_numeric_value("switch", op)
                if value is None:
                    continue
            elif "line" in typ:
                element_type = "line"
                op = "close" if "close" in typ else ("open" if "open" in typ else None)
                if op is None:
                    continue
                attribute = "state"
                value = _resolve_numeric_value("line", op)
                if value is None:
                    continue
            elif "load" in typ or "generator" in typ:
                element_type = action.get("element_type") or (
                    "generator" if "generator" in typ else "load"
                )
                op = action.get("operation") or (
                    "increase"
                    if "increase" in typ
                    else ("decrease" if "decrease" in typ else None)
                )
                if op is None:
                    continue
                setpoints = action.get("setpoints") or []
                if not setpoints and action.get("targets"):
                    # Build synthetic entry to preserve legacy behaviour
                    targets = (
                        action.get("targets")
                        if isinstance(action.get("targets"), list)
                        else [action.get("targets")]
                    )
                    attribute_hint = action.get("attribute") or "P"
                    setpoints = [
                        {
                            "id": t,
                            "attribute": attribute_hint,
                            "delta_percent": action.get("percentage"),
                            "basis_value": None,
                            "absolute_value": None,
                            "element_type": element_type,
                        }
                        for t in targets
                    ]
                handled = False
                for entry in setpoints:
                    target_id = entry.get("id")
                    if not target_id:
                        continue
                    attribute = (
                        entry.get("attribute") or action.get("attribute") or "P"
                    ).upper()
                    absolute_value = entry.get("absolute_value")
                    if absolute_value is None:
                        basis = entry.get("basis_value")
                        delta = entry.get("delta_percent")
                        try:
                            delta = float(delta)
                        except (TypeError, ValueError):
                            delta = None
                        if basis is not None and delta is not None:
                            sign = 1.0 if op == "increase" else -1.0
                            absolute_value = basis * (1.0 + (delta / 100.0 * sign))
                    if absolute_value is None:
                        perc = action.get("percentage")
                        if perc is None:
                            continue
                        try:
                            perc_value = float(perc)
                        except (TypeError, ValueError):
                            continue
                        value = perc_value if op == "increase" else -perc_value
                    else:
                        value = float(absolute_value)

                    cmd = {
                        "command": "iidm_command",
                        "iidm_id": str(target_id),
                        "attribute": attribute,
                        "element_type": element_type,
                        "value": value,
                    }
                    if is_interval:
                        start_at = action.get("interval_start", default_start_time)
                        if current_time is not None and interval_lead is not None:
                            try:
                                start_at = float(current_time) + float(interval_lead)
                            except (TypeError, ValueError):
                                pass
                    else:
                        start_at = action.get("t_start", default_start_time)
                    if start_at is not None:
                        try:
                            cmd["t_start"] = float(start_at)
                        except (TypeError, ValueError):
                            pass
                    if metadata:
                        cmd["metadata"] = metadata
                    dsl_cmds.append(cmd)
                    handled = True
                if handled:
                    continue
                attribute = (action.get("attribute") or "P").upper()
                perc = action.get("percentage")
                if perc is None:
                    continue
                try:
                    perc_value = float(perc)
                except (TypeError, ValueError):
                    continue
                value = perc_value if op == "increase" else -perc_value
            else:
                continue

            elem = action.get("id") or action.get("target")
            if elem is None:
                continue
            ids = elem if isinstance(elem, list) else [elem]
            for eid in ids:
                cmd = {
                    "command": "iidm_command",
                    "iidm_id": str(eid),
                    "attribute": attribute,
                    "element_type": element_type,
                    "value": value,
                }
                start_at = (
                    default_start_time
                    if is_interval
                    else action.get("t_start", default_start_time)
                )
                if start_at is not None:
                    try:
                        cmd["t_start"] = float(start_at)
                    except (TypeError, ValueError):
                        pass
                if metadata:
                    cmd["metadata"] = metadata
                dsl_cmds.append(cmd)
        except Exception:
            continue

    trainer_cmds = []
    for ctrl in raw_trainer_controls:
        try:
            cmd = _control_to_v2_command(ctrl)
            if cmd:
                trainer_cmds.append(cmd)
        except Exception:
            continue

    user_cmds = []
    for ctrl in raw_user_controls:
        try:
            cmd = _control_to_v2_command(ctrl)
            if cmd:
                user_cmds.append(cmd)
        except Exception:
            continue

    return _merge_commands_by_priority(dsl_cmds, trainer_cmds, user_cmds)


@router.post("/simulatorcontrol_v2")
def simulator_control_v2(input_data: AggregateInput):
    """Return atomic IIDM commands (schema v2) for the current step using ONLY the persistent EventStore.

    - Includes both DSL and user events from the store (no in-memory queue)
    - Promotes dependency-based events prior to selection
    """
    try:
        simulation_controller = get_simulation_controller()
        event_store = get_event_store()
        interpreter = simulation_controller.interpreter
        if interpreter is None:
            raise HTTPException(status_code=400, detail="Simulation not initialized.")
        # Record the absolute clock from the caller for this simulation
        try:
            set_current_time(
                simulation_controller.simulation_name, input_data.current_time
            )
        except ClockRegressionError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        except Exception:
            pass
        current_time = input_data.current_time
        eps = max(1e-3, (interpreter.time_step or 0) / 10.0)

        try:
            delay = interpreter.time_step or eps
            event_store.promote_ready_events(
                current_time,
                simulation=simulation_controller.simulation_name,
                delay=delay,
            )
        except Exception:
            pass

        due = event_store.events_due(
            current_time,
            eps,
            simulation=simulation_controller.simulation_name,
        )

        raw_actions, raw_user_controls, raw_trainer_controls, point_ids, completion_ids = (
            _partition_due_events(
                due,
                current_time,
            )
        )

        lead = interpreter.time_step or eps
        default_start_time = current_time + lead
        cmds = _to_v2_commands_from_inputs(
            raw_actions,
            raw_trainer_controls,
            raw_user_controls,
            default_start_time=default_start_time,
            interval_lead=lead,
            current_time=current_time,
        )

        # Mirror NATS path semantics: only mark as completed those DSL
        # events that actually produced commands (prevents dependants from
        # promoting when parent fails to build).
       
        try:
            success_ids = _command_event_ids(cmds, current_time=current_time)
            completed_ids = set(success_ids) | set(completion_ids)
            if completed_ids:
                event_store.mark_completed(list(completed_ids))
        except Exception:
            pass



        return _strip_command_metadata(cmds)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in simulator_control_v2: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
