"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Manage user-submitted controls and upcoming actions for simulations.

The user control manager translates inbound API payloads into the
normalized structures expected by the DSL interpreter and event store
while keeping track of simulator timing information.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ...utils.clock import get_current_time

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)


class UserControlManager:
    """Coordinate parsing, validation, and persistence of user controls."""

    def __init__(self, simulation_controller, event_store=None):
        """
        Initialize the manager with shared controller dependencies.

        Args:
            simulation_controller: SimulationController instance that
                exposes interpreter state used for validation.
            event_store: Optional EventStore responsible for persisting
                controls alongside DSL-scheduled actions.
        """
        self.simulation_controller = simulation_controller
        self.event_store = event_store
        logger.debug("UserControlManager initialized with event store integration.")

    def is_simulation_initialized(self):
        """Check if the simulation has been initialized."""
        return self.simulation_controller.interpreter is not None

    def is_simulation_initialized(self):
        """Check if the simulation has been initialized."""
        return self.simulation_controller.interpreter is not None

    def parse_control(self, control: dict) -> dict:
        """
        Normalize a single-target control payload from the API layer.

        Args:
            control (dict): Raw JSON payload describing the control.

        Returns:
            dict: Copy of the payload with coerced casing, types, and
            required fields.

        Raises:
            ValueError: If required fields such as ``value`` or
            ``timestamp`` are missing or invalid for the control type.

        Examples:
            >>> mgr.parse_control({'control_type': 'Load', 'action': 'SHED', 'id': 1, 'value': 5, 'timestamp': 10})
            {'control_type': 'load', 'action': 'shed', 'id': '1', 'timestamp': 10.0, 'value': 5.0}
        """
        logger.debug("Parsing control command: %s", control)
        parsed = dict(control)
        parsed["control_type"] = self._to_lower_str(parsed.get("control_type"))
        parsed["action"] = self._to_lower_str(parsed.get("action"))
        parsed["id"] = str(parsed.get("id", ""))
        parsed["timestamp"] = self._coerce_float(parsed.get("timestamp"), "timestamp")

        if parsed["control_type"] in {"load", "generator"}:
            if parsed.get("value") is None:
                logger.error(
                    "Missing value for control_type %s", parsed["control_type"]
                )
                raise ValueError("For load/generator, 'value' must be provided.")
            parsed["value"] = self._coerce_float(parsed.get("value"), "value")

        logger.debug("Parsed control command: %s", parsed)
        return parsed

    def add_control(self, control: dict) -> dict:
        """
        Validate, persist, and acknowledge an individual control action.

        Args:
            control (dict): Normalized control payload produced by
                `parse_control`.

        Returns:
            dict: Confirmation message suitable for API responses.

        Raises:
            ValueError: If the simulation has not been initialized.
        """
        if not self.is_simulation_initialized():
            raise ValueError("Simulation must be initialized before adding controls.")
        logger.debug("Adding control command: %s", control)
        # Persist to event store
        try:
            if self.event_store is not None:
                evt_type = f"{control['action']}_{control['control_type']}"
                payload = (
                    {"value": float(control["value"])}
                    if control.get("value") is not None
                    else None
                )
                self.event_store.enqueue_event(
                    source="user",
                    type=evt_type,
                    target=str(control.get("id")),
                    payload=payload,
                    time_spec="point",
                    at=float(control["timestamp"]),
                    idempotency_key=f"user:{self.simulation_controller.simulation_name}:{evt_type}:{control.get('id')}:{control['timestamp']}:{(payload or {}).get('value', '')}",
                    simulation=self.simulation_controller.simulation_name,
                )
        except Exception as e:
            logger.warning("Failed to persist user control to event store: %s", e)
        return {"message": "User control command added."}

    def get_controls_for_step(self, current_time: float) -> list:
        """
        Retrieve user-originated controls that are due at `current_time`.

        Args:
            current_time (float): Simulation timestamp to query.

        Returns:
            list: Controls converted into API-friendly dictionaries.

        Examples:
            >>> mgr.get_controls_for_step(42.0)
            [{'control_type': 'switch', 'action': 'open', 'id': 'sw-1', 'timestamp': 42.0}]
        """
        logger.debug("Retrieving controls for simulation time: %s", current_time)
        if self.event_store is None:
            return []
        if not self.is_simulation_initialized():
            logger.debug("Simulation not initialized; no controls available.")
            return []

        interpreter = self.simulation_controller.interpreter
        eps = self._time_epsilon(interpreter)

        simulation_name = self.simulation_controller.simulation_name
        try:
            due = self.event_store.events_due(
                current_time, eps, simulation=simulation_name
            )
        except Exception as exc:
            logger.warning("Failed to retrieve user controls from event store: %s", exc)
            return []

        controls: List[Dict[str, Any]] = []
        point_ids: List[str] = []
        for evt in due.get("points", []):
            if evt.get("source") != "user":
                continue
            ctrl = self._event_to_control(evt)
            if ctrl is not None:
                controls.append(ctrl)
                point_ids.append(evt.get("id"))

        if point_ids:
            try:
                self.event_store.mark_completed(point_ids)
            except Exception as exc:
                logger.warning("Failed to mark user events completed: %s", exc)

        logger.debug(
            "Resolved %d user controls for time %s", len(controls), current_time
        )
        return controls

    def parse_cluster_control(self, control: Dict) -> Dict:
        """
        Normalize a cluster-oriented control request.

        Args:
            control (Dict): Raw payload describing targets and metadata.

        Returns:
            Dict: Parsed structure containing cluster classification,
            timestamp, and optional value hints.

        Raises:
            ValueError: When the target specification is missing or does
            not meet the validation rules for static or dynamic clusters.
        """
        logger.debug("Parsing cluster control command: %s", control)
        parsed = control.copy()

        parsed["control_type"] = str(parsed.get("control_type", "")).lower()
        parsed["action"] = str(parsed.get("action", "")).lower()

        if "target" not in parsed:
            logger.error("Missing target in cluster control command")
            raise ValueError("Target must be provided.")

        if isinstance(parsed["target"], list):
            if not all(isinstance(id, str) for id in parsed["target"]):
                logger.error("Static cluster target must be a list of strings")
                raise ValueError(
                    "Static cluster target must be a list of component IDs (strings)."
                )
            parsed["cluster_type"] = "static"
            parsed["component_ids"] = parsed["target"]
        elif (
            isinstance(parsed["target"], dict)
            and parsed["target"].get("type") == "dynamic_cluster"
        ):
            if "relationship" not in parsed["target"]:
                logger.error("Dynamic cluster missing relationship specification")
                raise ValueError(
                    "Dynamic cluster must include relationship specification."
                )
            relationship = parsed["target"]["relationship"]
            if not all(k in relationship for k in ["filter_type", "component_type"]):
                logger.error("Invalid dynamic cluster relationship: %s", relationship)
                raise ValueError(
                    "Dynamic cluster relationship must include filter_type and component_type."
                )
            if relationship["filter_type"] not in ["regex", "group_by", "property"]:
                logger.error("Invalid filter_type: %s", relationship["filter_type"])
                raise ValueError(
                    "filter_type must be 'regex', 'group_by', or 'property'."
                )
            parsed["cluster_type"] = "dynamic"
            parsed["relationship"] = relationship
            parsed["component_ids"] = None
        else:
            logger.error("Invalid target format: %s", parsed["target"])
            raise ValueError(
                "Target must be a list of component IDs (static) or dynamic cluster (dict)."
            )

        parsed["timestamp"] = self._coerce_float(parsed.get("timestamp"), "timestamp")

        if parsed["control_type"] in ["load", "generator"]:
            if parsed.get("value") is None:
                logger.error(
                    "Missing value for control_type %s", parsed["control_type"]
                )
                raise ValueError("For load/generator, 'value' must be provided.")
            parsed["value"] = self._coerce_float(parsed.get("value"), "value")

        logger.debug("Parsed cluster control command: %s", parsed)
        return parsed

    def add_cluster_control(self, control: Dict) -> Dict:
        """
        Expand a cluster control into per-component actions.

        Args:
            control (Dict): Raw cluster definition supplied by the API.

        Returns:
            Dict: Confirmation message returned to the caller.

        Raises:
            ValueError: If the simulation is uninitialized or the
            resolved cluster has no members.
        """
        if not self.is_simulation_initialized():
            raise ValueError("Simulation must be initialized before adding controls.")
        logger.debug("Adding cluster control command: %s", control)
        parsed_control = self.parse_cluster_control(control)

        if parsed_control["cluster_type"] == "dynamic":
            component_ids = self.resolve_dynamic_targets(parsed_control["relationship"])
            if not component_ids:
                logger.warning(
                    "Dynamic cluster %s resolved to no components",
                    parsed_control["relationship"],
                )
                # Fail fast so API returns 400 to the client
                raise ValueError("Dynamic cluster resolved to zero components")
        else:
            component_ids = parsed_control["component_ids"]
            if not component_ids:
                logger.warning("Static cluster is empty")
                # Fail fast so API returns 400 to the client
                raise ValueError("Static cluster resolved to zero components")

        for component_id in component_ids:
            individual_control = {
                "control_type": parsed_control["control_type"],
                "action": parsed_control["action"],
                "id": component_id,
                "timestamp": parsed_control["timestamp"],
            }
            if "value" in parsed_control:
                individual_control["value"] = parsed_control["value"]
            logger.debug(
                "Prepared individual control for component %s: %s",
                component_id,
                individual_control,
            )
            self.add_control(individual_control)

        return {"message": "Cluster control command added."}

    def resolve_dynamic_targets(self, relationship: Dict) -> List[str]:
        """
        Resolve a dynamic cluster specification via the DSL interpreter.

        Args:
            relationship (Dict): Relationship filter describing target
                matching rules.

        Returns:
            List[str]: Component identifiers matching the relationship.

        Raises:
            ValueError: If the simulation is not initialized or the DSL
            interpreter rejects the relationship.
        """
        interpreter = self.simulation_controller.interpreter
        if interpreter is None:
            logger.error("Simulation not initialized for dynamic cluster resolution")
            raise ValueError("Simulation not initialized.")

        try:
            component_ids = interpreter.resolve_dynamic_cluster(relationship)
            logger.debug(
                "Resolved dynamic cluster %s to %d components: %s",
                relationship,
                len(component_ids),
                component_ids,
            )
            return component_ids
        except Exception as e:
            logger.error(
                "Failed to resolve dynamic cluster %s: %s", relationship, str(e)
            )
            raise ValueError(f"Failed to resolve dynamic cluster: {str(e)}") from e

    def next_step_controls(self, limit: int = 200) -> Dict[str, Any]:
        """Peek at upcoming actions (DSL + user) scheduled for the next simulation step."""

        current_time = self._current_simulation_time()
        time_step = self._time_step_or_zero()
        target_time = self._next_step_time(current_time, time_step)

        snapshot = {
            "current_time": current_time,
            "time_step": time_step,
            "next_time": target_time,
            "controls": [],
        }

        if self.event_store is None or not self.is_simulation_initialized():
            return snapshot

        try:
            events = self.event_store.list_events(
                simulation=self.simulation_controller.simulation_name,
                limit=limit,
                offset=0,
            )
        except Exception as exc:
            logger.warning("Failed to list upcoming events: %s", exc)
            return snapshot

        interpreter = self.simulation_controller.interpreter
        eps = self._time_epsilon(interpreter)

        upcoming_dsl: List[Tuple[float, Dict[str, Any]]] = []
        upcoming_user: List[Tuple[float, Dict[str, Any]]] = []
        for evt in events:
            status = str(evt.get("status", "")).lower()
            if status not in {"pending", "scheduled", "active"}:
                continue
            due_time = evt.get("due_at") or evt.get("at") or evt.get("interval_start")
            try:
                due_time = float(due_time)
            except (TypeError, ValueError):
                continue
            if due_time + eps < current_time:
                continue
            source = str(evt.get("source", "")).lower()
            if source == "user":
                upcoming_user.append((due_time, evt))
            else:
                upcoming_dsl.append((due_time, evt))

        relevant_events: List[Tuple[float, Dict[str, Any]]] = []
        if target_time is None:
            combined = upcoming_dsl + upcoming_user
            if not combined:
                return snapshot
            candidate_time = min(t for t, _ in combined)
        else:
            candidate_time = target_time
        snapshot["next_time"] = candidate_time

        upcoming_dsl.sort(key=lambda item: item[0])
        upcoming_user.sort(key=lambda item: item[0])

        for due_time, evt in upcoming_dsl:
            if abs(due_time - candidate_time) <= eps:
                relevant_events.append((due_time, evt))
        for due_time, evt in upcoming_user:
            if abs(due_time - candidate_time) <= eps:
                relevant_events.append((due_time, evt))

        if not relevant_events:
            return snapshot

        combined_actions: List[Dict[str, Any]] = []

        for due_time, evt in relevant_events:
            source = str(evt.get("source", "")).lower()
            if source == "user":
                ctrl = self._event_to_control(evt)
                if ctrl is None:
                    continue
                ctrl.setdefault("timestamp", due_time)
                combined_actions.append(ctrl)
            else:
                action_data = self._store_event_to_action(evt)
                if str(evt.get("time_spec", "")).lower() == "interval":
                    container = {
                        "action": action_data,
                        "interval_start": evt.get("interval_start"),
                        "interval_end": evt.get("interval_end"),
                        "law": evt.get("law"),
                    }
                    mapped = self._transform_dsl_action(container, due_time)
                else:
                    mapped = self._transform_dsl_action(action_data, due_time)
                combined_actions.append(mapped)

        snapshot["controls"] = combined_actions
        return snapshot

    def _event_to_control(self, evt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert an event-store record into a user control representation.

        Args:
            evt (Dict[str, Any]): Event payload from the persistent store.

        Returns:
            Optional[Dict[str, Any]]: Control dictionary when a valid
            target id exists, otherwise ``None``.
        """
        event_type = str(evt.get("type", "") or "")
        if "_" in event_type:
            action, control_type = event_type.split("_", 1)
        else:
            action = event_type
            control_type = ""

        control_type = control_type or str(evt.get("control_type", ""))
        timestamp = evt.get("due_at") or evt.get("at")
        try:
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            timestamp = (
                float(self.simulation_controller.interpreter.current_time)
                if self.simulation_controller and self.simulation_controller.interpreter
                else 0.0
            )

        payload = evt.get("payload") or {}
        target = evt.get("target")
        if isinstance(target, list):
            target = target[0] if target else None

        control = {
            "control_type": control_type,
            "action": action,
            "id": target,
            "timestamp": timestamp,
        }

        if payload and payload.get("value") is not None:
            control["value"] = payload["value"]

        return control if control.get("id") else None

    @staticmethod
    def _to_lower_str(value: Optional[str]) -> str:
        """
        Safely normalize a value to a lowercase string.

        Args:
            value (Optional[str]): Input value that may be ``None``.

        Returns:
            str: Lowercase string representation.
        """
        return str(value or "").lower()

    @staticmethod
    def _coerce_float(value: Any, field_name: str) -> float:
        """
        Convert arbitrary input to float while reporting context on error.

        Args:
            value (Any): Value to convert.
            field_name (str): Name used in error messages.

        Returns:
            float: Converted numeric value.

        Raises:
            ValueError: If conversion fails.
        """
        try:
            return float(value)
        except Exception as exc:
            logger.error("Error converting %s to float: %s", field_name, exc)
            raise ValueError(f"{field_name} must be a number (float).") from exc

    @staticmethod
    def _store_event_to_action(evt: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate a stored DSL event into a simplified action dict.

        Args:
            evt (Dict[str, Any]): Event record returned by the store.

        Returns:
            Dict[str, Any]: Action metadata containing ids, percentages,
            and any DSL-provided metadata.
        """
        typ = str(evt.get("type", "")).lower()
        target = evt.get("target")
        payload = evt.get("payload") or {}
        action: Dict[str, Any] = {"type": typ}
        if isinstance(target, str):
            action["id"] = target
        elif target is not None:
            action["target"] = target
        if "percentage" in payload and payload["percentage"] is not None:
            action["percentage"] = payload["percentage"]
        if "metadata" in evt and evt["metadata"] is not None:
            action["metadata"] = evt["metadata"]
        return action

    @staticmethod
    def _transform_dsl_action(
        raw_action: Dict[str, Any], timestamp: float
    ) -> Dict[str, Any]:
        """
        Convert a DSL action or interval container into timeline output.

        Args:
            raw_action (Dict[str, Any]): Action data or wrapper returned
                by `_store_event_to_action`.
            timestamp (float): Execution time associated with the action.

        Returns:
            Dict[str, Any]: Structure that downstream clients expect,
            including metadata for interval-based actions.
        """
        action = raw_action
        interval_info = None

        if isinstance(raw_action, dict) and "action" in raw_action:
            interval_info = {
                "start": raw_action.get("interval_start", timestamp),
                "end": raw_action.get("interval_end", timestamp),
                "law": raw_action.get("law"),
            }
            action = raw_action.get("action")

        if not isinstance(action, dict):
            return {
                "timestamp": timestamp,
                "actionType": str(action),
                "details": {},
            }

        typ = action.get("type", "")
        is_fault = "fault" in typ
        action_type = typ if is_fault else typ.split("_")[0] if typ else ""

        details: Dict[str, Any] = {}
        if is_fault:
            details = {
                "component_type": action.get("component_type", "line"),
                "id": action.get("id"),
            }
        else:
            details = {"elementId": action.get("id") or action.get("target")}
            if "load" in typ or "generator" in typ:
                details["percentage"] = action.get("percentage")

        transformed = {
            "timestamp": timestamp,
            "actionType": action_type,
            "details": details,
        }

        if interval_info:
            transformed["interval_start"] = interval_info.get("start")
            transformed["interval_end"] = interval_info.get("end")
            transformed["law"] = interval_info.get("law")

        if "metadata" in action:
            transformed["metadata"] = action["metadata"]

        return transformed

    def _current_simulation_time(self) -> float:
        """
        Compute the authoritative simulation time considering clock drift.

        Returns:
            float: Maximum of the interpreter's current time and the
            distributed clock cache for the simulation.
        """
        interpreter = self.simulation_controller.interpreter
        sim_name = getattr(self.simulation_controller, "simulation_name", None)
        clock_time = 0.0
        if sim_name:
            try:
                clock_time = float(get_current_time(sim_name) or 0.0)
            except Exception:
                clock_time = 0.0
        try:
            interpreter_time = float(getattr(interpreter, "current_time", 0.0) or 0.0)
        except (TypeError, ValueError):
            interpreter_time = 0.0
        return max(clock_time, interpreter_time)

    def _time_step_or_zero(self) -> float:
        """
        Return the interpreter's configured time step or default to zero.

        Returns:
            float: Positive time-step value if present, else ``0.0``.
        """
        interpreter = self.simulation_controller.interpreter
        try:
            return float(getattr(interpreter, "time_step", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _time_epsilon(self, interpreter) -> float:
        """
        Calculate a tolerance used when comparing float-based timestamps.

        Args:
            interpreter: DSL interpreter exposing ``time_step``.

        Returns:
            float: Minimum epsilon scaled by the time step.
        """
        eps = 1e-3
        try:
            step = float(getattr(interpreter, "time_step", 0.0) or 0.0)
        except (TypeError, ValueError):
            step = 0.0
        if step:
            eps = max(eps, step / 10.0)
        return eps

    @staticmethod
    def _next_step_time(current_time: float, time_step: float) -> Optional[float]:
        """
        Compute the timestamp for the next simulation step.

        Args:
            current_time (float): Present simulation timestamp.
            time_step (float): Positive time-step interval.

        Returns:
            Optional[float]: Sum of ``current_time`` and ``time_step`` or
            ``None`` when no time step is configured.
        """
        if time_step and time_step > 0:
            return current_time + time_step
        return None
