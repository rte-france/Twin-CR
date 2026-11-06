"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Manage dynamic DSL value subscriptions based on pending dependency events.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, Optional, Set

from ..domain.controllers.global_instances import (
    get_event_store,
    get_simulation_controller,
)


logger = logging.getLogger(__name__)


ACTIVE_STATUSES = {"pending", "scheduled", "active", "locked"}


def _attribute_token(attribute: Optional[str]) -> str:
    """
    Normalize measurement attributes into canonical token names.

    Args:
        attribute (Optional[str]): Attribute value such as ``P`` or ``Q``.

    Returns:
        str: Normalized attribute token.
    """
    attr = (attribute or "P").strip().upper()
    if attr == "P":
        return "power_active"
    if attr == "Q":
        return "power_reactive"
    return attr.lower()


class DependencySubscriptionManager:
    """Track DSL value subscriptions needed for condition-based events."""

    def __init__(self) -> None:
        """Initialize empty tracking structures for subscriptions."""
        self._active_keys: Set[str] = set()
        self._current_simulation: Optional[str] = None
        self._key_sources: Dict[str, Set[str]] = {}

    def sync(self) -> tuple[Set[str], Set[str]]:
        """Return the subscription additions/removals required to match current dependencies."""

        simulation_controller = get_simulation_controller()
        interpreter = getattr(simulation_controller, "interpreter", None)
        simulation_name = (
            simulation_controller.simulation_name if interpreter is not None else None
        )

        removals: Set[str] = set()
        if simulation_name != self._current_simulation:
            removals |= self._active_keys
            self._active_keys = set()
            self._current_simulation = simulation_name
            self._key_sources = {}

        if not simulation_name or interpreter is None:
            return set(), removals

        desired, source_map = self._collect_desired_keys(simulation_name)
        to_add = desired - self._active_keys
        removals |= self._active_keys - desired
        self._active_keys = desired
        self._key_sources = source_map
        return to_add, removals

    def reset(self) -> None:
        """Clear the currently tracked subscriptions."""

        self._active_keys.clear()
        self._current_simulation = None
        self._key_sources = {}

    def record_subscription(
        self,
        measurement_key: str,
        simulation_name: Optional[str],
        source: Optional[str] = None,
    ) -> None:
        """Remember a subscription that was registered outside the periodic sync."""

        if not measurement_key:
            return
        if simulation_name and simulation_name != self._current_simulation:
            # A manual subscription on a different simulation implies we should
            # reset our local cache to avoid leaking keys from the previous run.
            self._active_keys.clear()
            self._current_simulation = simulation_name
        if self._current_simulation is None and simulation_name:
            self._current_simulation = simulation_name
        if self._current_simulation is None:
            # Without a known simulation we cannot reconcile later, so defer.
            return
        self._active_keys.add(measurement_key)
        if source:
            token = str(source).strip().lower()
            if token:
                self._key_sources.setdefault(measurement_key, set()).add(token)

    def sources_for_key(self, measurement_key: str) -> Set[str]:
        """
        Return the set of sources that required a measurement key.

        Args:
            measurement_key (str): Key captured within `_key_sources`.

        Returns:
            Set[str]: Source labels such as ``dsl`` or ``user``.
        """
        sources = self._key_sources.get(measurement_key)
        if not sources:
            return set()
        return set(sources)

    def _collect_desired_keys(
        self, simulation_name: str
    ) -> tuple[Set[str], Dict[str, Set[str]]]:
        """
        Determine which measurement keys should be subscribed for a simulation.

        Args:
            simulation_name (str): Simulation namespace to inspect.

        Returns:
            tuple: Desired keys and a mapping of key -> set of sources.
        """
        event_store = get_event_store()
        desired: Set[str] = set()
        source_map: Dict[str, Set[str]] = defaultdict(set)

        offset = 0
        page_size = 500
        while True:
            try:
                events = event_store.list_events(
                    time_spec="condition",
                    simulation=simulation_name,
                    limit=page_size,
                    offset=offset,
                )
            except Exception as exc:  # pragma: no cover - best effort
                logger.debug(
                    "Failed to list condition events for %s: %s", simulation_name, exc
                )
                break

            if not events:
                break

            for event in events:
                status = (event.get("status") or "").lower()
                if status not in ACTIVE_STATUSES:
                    continue
                expr = event.get("condition_expr")
                condition_keys = self._extract_variables(expr)
                desired |= condition_keys
                for key in condition_keys:
                    if key:
                        source_map[key].add("dsl")

            if len(events) < page_size:
                break
            offset += page_size

        setpoint_keys, setpoint_sources = self._collect_setpoint_keys(
            event_store, simulation_name
        )
        desired |= setpoint_keys
        for key, sources in setpoint_sources.items():
            if not sources:
                source_map[key].add("dsl")
                continue
            source_map[key].update(sources)
        return desired, dict(source_map)

    def _extract_variables(self, node) -> Set[str]:
        """
        Recursively traverse a condition expression to find measurement keys.

        Args:
            node: JSON-like structure describing a DSL condition.

        Returns:
            Set[str]: Serialized measurement keys referenced by the node.
        """
        if isinstance(node, dict):
            result: Set[str] = set()
            node_type = node.get("type")
            if node_type in {
                "voltage",
                "frequency",
                "power_flow",
                "active_flow",
                "reactive_flow",
            } and node.get("id"):
                component = node.get("component")
                identifier = node.get("id")
                key = self._serialize_variable(node_type, component, identifier)
                if key:
                    result.add(key)
            for value in node.values():
                result |= self._extract_variables(value)
            return result
        if isinstance(node, list):
            result: Set[str] = set()
            for item in node:
                result |= self._extract_variables(item)
            return result
        return set()

    @staticmethod
    def _serialize_variable(
        var_type: str, component: Optional[str], identifier: Optional[str]
    ) -> Optional[str]:
        """
        Turn a variable description into a measurement key string.

        Args:
            var_type (str): Measurement type (voltage, power_flow, etc.).
            component (Optional[str]): Component category filter.
            identifier (Optional[str]): IIDM identifier for the element.

        Returns:
            Optional[str]: Serialized key or ``None`` if identifier missing.
        """
        if not identifier:
            return None
        if component:
            return f"{var_type}:{component}:{identifier}"
        return f"{var_type}:{identifier}"

    def _collect_setpoint_keys(
        self, event_store, simulation_name: str
    ) -> tuple[Set[str], Dict[str, Set[str]]]:
        """
        Inspect pending events to collect measurement keys referenced by setpoints.

        Args:
            event_store: EventStore instance.
            simulation_name (str): Simulation whose events should be scanned.

        Returns:
            tuple: Keys discovered and mapping of key -> sources.
        """
        keys: Set[str] = set()
        source_map: Dict[str, Set[str]] = defaultdict(set)
        page_size = 500
        statuses = ACTIVE_STATUSES

        for status in statuses:
            offset = 0
            while True:
                try:
                    events = event_store.list_events(
                        status=status,
                        simulation=simulation_name,
                        limit=page_size,
                        offset=offset,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug(
                        "Failed to list %s events for %s: %s",
                        status,
                        simulation_name,
                        exc,
                    )
                    break

                if not events:
                    break

                for event in events:
                    event_type = str(event.get("type", "")).lower()
                    if "load" not in event_type and "generator" not in event_type:
                        continue
                    payload = event.get("payload") or {}
                    extracted = self._extract_measurement_keys_from_payload(
                        payload, event
                    )
                    if not extracted:
                        continue
                    source = str(event.get("source") or "").strip().lower() or "dsl"
                    keys |= extracted
                    for key in extracted:
                        source_map[key].add(source)

                if len(events) < page_size:
                    break
                offset += page_size

        return keys, dict(source_map)

    @staticmethod
    def _extract_measurement_keys_from_payload(payload: dict, event: dict) -> Set[str]:
        """
        Infer measurement keys from an event payload or its metadata.

        Args:
            payload (dict): Event payload containing targets/setpoints.
            event (dict): Full event used to derive defaults.

        Returns:
            Set[str]: Measurement keys referenced by the payload.
        """
        extracted: Set[str] = set()
        if not payload:
            payload = {}
        event_type = str(event.get("type", "")).lower()
        operation = str(payload.get("operation") or "").lower()
        is_set = operation == "set" or event_type.startswith("set_")
        if is_set:
            time_spec = str(event.get("time_spec") or "").lower()
            law = str(event.get("law") or "").lower()
            if time_spec != "interval" or law != "linear":
                return extracted

        measurement_keys = payload.get("measurement_keys") or []
        if isinstance(measurement_keys, dict):
            measurement_keys = measurement_keys.values()
        for key in measurement_keys:
            if key:
                extracted.add(str(key))
        if extracted:
            return extracted

        attribute = (
            payload.get("attribute")
            or (payload.get("setpoint") or {}).get("attribute")
            or "P"
        ).upper()
        element_type = payload.get("element_type")
        if not element_type:
            if "generator" in event_type:
                element_type = "generator"
            elif "load" in event_type:
                element_type = "load"

        if not element_type:
            return extracted

        element_type = str(element_type).lower()

        targets = payload.get("targets")
        if targets is None:
            targets = event.get("target")

        if isinstance(targets, str):
            targets_iterable = [targets]
        elif isinstance(targets, list):
            targets_iterable = targets
        else:
            targets_iterable = []

        for target in targets_iterable:
            if not target:
                continue
            token = str(target).strip()
            if not token:
                continue
            attr_token = _attribute_token(attribute)
            extracted.add(f"{attr_token}:{element_type}:{token}")

        return extracted


__all__ = ["DependencySubscriptionManager"]
