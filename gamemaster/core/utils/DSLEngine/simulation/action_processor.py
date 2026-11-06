"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

_FROZEN_BASES: Dict[str, Dict[str, float]] = {}


class ActionProcessor:
    """Processes and normalizes actions for power system elements."""

    VALID_ELEMENTS = {"load", "generator"}

    @staticmethod
    def normalize_attribute_value(attribute: Optional[str]) -> str:
        """Normalize attribute to P, Q, or state."""
        attr = (attribute or "P").strip()
        upper = attr.upper()

        if upper in {"P", "Q"}:
            return upper
        if attr.lower() == "state":
            return "state"
        return attr

    @classmethod
    def normalize_attribute_token(cls, attribute: Optional[str]) -> str:
        """Convert attribute to token format."""
        attr = cls.normalize_attribute_value(attribute)
        mapping = {"P": "power_active", "Q": "power_reactive"}
        return mapping.get(attr, attr.lower())

    @classmethod
    def parse_channel(cls, channel_ctx) -> str:
        """Parse channel context, defaulting to P."""
        if channel_ctx is None:
            return "P"
        return cls.normalize_attribute_value(channel_ctx.getText())

    @classmethod
    def measurement_key(cls, element_type: str, attribute: str, target_id: str) -> Optional[str]:
        """Generate measurement key for element."""
        if not target_id:
            return None

        element = (element_type or "").strip().lower()
        if not element:
            return None

        attr_token = cls.normalize_attribute_token(attribute)
        return f"{attr_token}:{element}:{str(target_id).strip()}"

    @staticmethod
    def lookup_measurement(system_state: Optional[dict], key: Optional[str]) -> Optional[float]:
        """Lookup measurement value from system state."""
        if not key or not system_state:
            return None

        value = system_state.get(key)
        if value is None:
            system_state.get(key.lower())

        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @classmethod
    def _extract_frozen_basis(cls, action: dict) -> Dict[str, float]:
        """Extract frozen basis values from action metadata and global cache."""
        meta = action.get("metadata")
        if not isinstance(meta, dict):
            return {}

        frozen_basis = meta.get("frozen_basis") or {}
        if not isinstance(frozen_basis, dict):
            frozen_basis = {}

        event_id = meta.get("event_id")
        if event_id:
            event_key = str(event_id)
            if event_key in _FROZEN_BASES:
                frozen_basis = {**_FROZEN_BASES[event_key], **frozen_basis}

        return frozen_basis

    @classmethod
    def _get_basis_value(
        cls,
        target_id: str,
        existing_setpoint: Optional[dict],
        default_setpoint: dict,
        frozen_basis: dict,
        system_state: Optional[dict],
        measurement_key: Optional[str],
        is_single_target: bool
    ) -> Optional[float]:
        """Determine basis value from multiple sources in priority order."""
        # Priority 1: Existing setpoint
        if existing_setpoint and existing_setpoint.get("basis_value") is not None:
            try:
                return float(existing_setpoint["basis_value"])
            except (TypeError, ValueError):
                pass

        # Priority 2: Default setpoint (only for single target)
        if is_single_target and default_setpoint:
            try:
                basis = default_setpoint.get("basis_value")
                if basis is not None:
                    return float(basis)
            except (TypeError, ValueError):
                pass

        # Priority 3: Frozen basis
        if frozen_basis:
            try:
                basis = frozen_basis.get(str(target_id))
                if basis is not None:
                    return float(basis)
            except (TypeError, ValueError):
                pass

        # Priority 4: Lookup from system state
        basis = cls.lookup_measurement(system_state, measurement_key)
        if basis is not None:
            frozen_basis[str(target_id)] = basis

        return basis

    @classmethod
    def _calculate_absolute_value(cls, basis: Optional[float], delta_percent: float, sign: float) -> Optional[float]:
        """Calculate absolute value from basis and percentage delta."""
        if basis is None:
            return None
        return basis * (1.0 + (delta_percent / 100.0 * sign))

    @classmethod
    def _build_setpoint_entry(
        cls,
        target_id: str,
        attribute: str,
        delta_percent: float,
        basis: Optional[float],
        measurement_key: Optional[str],
        direction: str,
        element_type: str
    ) -> Dict[str, Any]:
        """Build a single setpoint entry."""
        absolute = cls._calculate_absolute_value(basis, delta_percent, 1.0 if direction == "increase" else -1.0)

        return {
            "id": target_id,
            "attribute": attribute,
            "delta_percent": delta_percent,
            "basis_value": basis,
            "absolute_value": absolute,
            "measurement_key": measurement_key,
            "operation": direction,
            "element_type": element_type,
        }

    @classmethod
    def _normalize_targets(cls, action: dict, materialize_target: Callable, normalize_targets: Callable) -> List[str]:
        """Normalize and materialize target specifications."""
        if action.get("target_spec"):
            refreshed = materialize_target(action["target_spec"])
            targets = normalize_targets(refreshed)
            action["targets"] = targets
            action["target"] = targets[0] if len(targets) == 1 else targets
            return targets

        targets = action.get("targets")
        if not targets:
            targets = normalize_targets(action.get("target"))
            action["targets"] = targets
            action["target"] = targets[0] if len(targets) == 1 else ([] if not targets else targets)

        return targets

    @classmethod
    def _is_set_action(cls, action: dict) -> bool:
        """Identify actions that set absolute values."""
        operation = str(action.get("operation") or "").lower()
        if operation == "set":
            return True
        action_type = str(action.get("type") or "").lower()
        if action_type.startswith("set_"):
            return True
        return False

    @classmethod
    def _prepare_set_action(
        cls,
        action: dict,
        *,
        attribute: str,
        element_type: str,
        targets: List[str],
        system_state: Optional[dict] = None,
    ) -> dict:
        """Normalize absolute setpoint actions."""
        action["operation"] = "set"
        action.setdefault("element_type", element_type)
        action.setdefault("attribute", attribute)

        frozen_basis = cls._extract_frozen_basis(action)
        setpoint = action.get("setpoint")
        if not isinstance(setpoint, dict):
            setpoint = {}
        setpoint.setdefault("attribute", attribute)

        absolute_value = setpoint.get("absolute_value")
        if absolute_value is None:
            absolute_value = action.get("value")
        try:
            absolute_value = float(absolute_value) if absolute_value is not None else None
        except (TypeError, ValueError):
            absolute_value = None
        if absolute_value is not None:
            setpoint["absolute_value"] = absolute_value

        from_value = setpoint.get("from_value")
        try:
            from_value = float(from_value) if from_value is not None else None
        except (TypeError, ValueError):
            from_value = None
        if from_value is not None:
            setpoint["from_value"] = from_value

        target_value = setpoint.get("target_value")
        if target_value is None:
            target_value = absolute_value
        try:
            target_value = float(target_value) if target_value is not None else None
        except (TypeError, ValueError):
            target_value = None
        if target_value is not None:
            setpoint["target_value"] = target_value
        action["setpoint"] = setpoint

        base_from_value = from_value
        setpoints = action.get("setpoints")
        if not isinstance(setpoints, list) or not setpoints:
            setpoints = []
            for target_id in targets:
                measurement_key = cls.measurement_key(element_type, attribute, target_id)
                entry_from = base_from_value
                if entry_from is None and target_id is not None:
                    cached = frozen_basis.get(str(target_id))
                    if cached is not None:
                        entry_from = cached
                if entry_from is None and system_state is not None:
                    entry_from = cls.lookup_measurement(system_state, measurement_key)
                if entry_from is not None:
                    frozen_basis[str(target_id)] = entry_from
                setpoints.append(
                    {
                        "id": target_id,
                        "attribute": attribute,
                        "absolute_value": absolute_value,
                        "target_value": target_value,
                        "from_value": entry_from,
                        "measurement_key": measurement_key,
                        "operation": "set",
                        "element_type": element_type,
                    }
                )
        else:
            for entry in setpoints:
                if not isinstance(entry, dict):
                    continue
                target_id = entry.get("id")
                if target_id is None:
                    continue
                entry.setdefault("attribute", attribute)
                if entry.get("absolute_value") is None and absolute_value is not None:
                    entry["absolute_value"] = absolute_value
                if entry.get("target_value") is None and target_value is not None:
                    entry["target_value"] = target_value
                entry.setdefault("operation", "set")
                entry.setdefault("element_type", element_type)
                if entry.get("measurement_key") is None:
                    measurement_key = cls.measurement_key(
                        element_type,
                        entry.get("attribute") or attribute,
                        target_id,
                    )
                    if measurement_key is not None:
                        entry["measurement_key"] = measurement_key
                entry_from = entry.get("from_value")
                if entry_from is None and from_value is not None:
                    entry_from = from_value
                if entry_from is None and target_id is not None:
                    cached = frozen_basis.get(str(target_id))
                    if cached is not None:
                        entry_from = cached
                if entry_from is None and system_state is not None:
                    entry_from = cls.lookup_measurement(
                        system_state, entry.get("measurement_key")
                    )
                if entry_from is not None:
                    entry["from_value"] = entry_from
                    frozen_basis[str(target_id)] = entry_from

        measurement_keys = [
            entry.get("measurement_key")
            for entry in setpoints
            if isinstance(entry, dict) and entry.get("measurement_key")
        ]
        action["setpoints"] = setpoints
        action["measurement_keys"] = measurement_keys

        cls._persist_frozen_basis(action, frozen_basis)

        if len(setpoints) == 1:
            entry = setpoints[0]
            if isinstance(entry, dict):
                action["setpoint"].update(
                    {
                        "attribute": entry.get("attribute"),
                        "absolute_value": entry.get("absolute_value"),
                        "target_value": entry.get("target_value"),
                        "from_value": entry.get("from_value"),
                        "measurement_key": entry.get("measurement_key"),
                    }
                )
        elif setpoints:
            action["setpoint"].update(
                {
                    "absolute_values": [
                        entry.get("absolute_value")
                        for entry in setpoints
                        if isinstance(entry, dict)
                    ],
                    "target_values": [
                        entry.get("target_value")
                        for entry in setpoints
                        if isinstance(entry, dict)
                    ],
                    "from_values": [
                        entry.get("from_value")
                        for entry in setpoints
                        if isinstance(entry, dict)
                    ],
                    "measurement_keys": measurement_keys,
                }
            )

        return action

    @classmethod
    def _get_delta_percent(cls, action: dict) -> float:
        """Extract delta percentage from action."""
        delta_percent = None

        if "setpoint" in action:
            delta_percent = action["setpoint"].get("delta_percent")
        if delta_percent is None:
            delta_percent = action.get("percentage")

        try:
            return float(delta_percent)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _get_operation_direction(cls, action: dict) -> str:
        """Determine operation direction (increase/decrease)."""
        direction = action.get("operation")
        if direction:
            return direction

        action_type = str(action.get("type", "")).lower()
        return "increase" if "increase" in action_type else "decrease"

    @classmethod
    def _update_action_setpoint(cls, action: dict, setpoint_entries: List[Dict[str, Any]], measurement_keys: List[str]):
        """Update action with computed setpoint data."""
        if len(setpoint_entries) == 1:
            entry = setpoint_entries[0]
            action["setpoint"].update({
                "basis_value": entry["basis_value"],
                "absolute_value": entry["absolute_value"],
                "measurement_key": entry["measurement_key"],
            })
        else:
            basis_values = [e["basis_value"] for e in setpoint_entries]
            absolute_values = [e["absolute_value"] for e in setpoint_entries]
            action["setpoint"].update({
                "basis_values": basis_values,
                "absolute_values": absolute_values,
                "measurement_keys": measurement_keys,
            })

    @classmethod
    def _persist_frozen_basis(cls, action: dict, frozen_basis: dict):
        """Persist frozen basis values in action metadata and global cache."""
        if not frozen_basis:
            return

        meta = action.get("metadata")
        if isinstance(meta, dict):
            meta = dict(meta)
            meta["frozen_basis"] = dict(frozen_basis)
            action["metadata"] = meta

            event_id = meta.get("event_id")
            if event_id:
                _FROZEN_BASES[str(event_id)] = dict(frozen_basis)

    @classmethod
    def prepare_action(
        cls,
        action: dict,
        system_state: Optional[dict],
        *,
        materialize_target: Callable[[object], List[str]],
        normalize_targets: Callable[[object], List[str]],
    ) -> dict:
        """Prepare action with normalized attributes and computed setpoints."""
        if not isinstance(action, dict):
            return action

        element_type = action.get("element_type")
        if element_type not in cls.VALID_ELEMENTS:
            return action

        # Normalize attribute
        raw_attribute = action.get("attribute") or action.get("setpoint", {}).get("attribute")
        attribute = cls.normalize_attribute_value(raw_attribute)
        action.setdefault("attribute", attribute)

        # Normalize targets
        targets = cls._normalize_targets(action, materialize_target, normalize_targets)

        if cls._is_set_action(action):
            return cls._prepare_set_action(
                action,
                attribute=attribute,
                element_type=element_type,
                targets=targets,
                system_state=system_state,
            )

        # Extract parameters
        delta_percent = cls._get_delta_percent(action)
        direction = cls._get_operation_direction(action)
        sign = 1.0 if direction == "increase" else -1.0

        # Initialize setpoint
        action.setdefault("setpoint", {})
        action["setpoint"]["attribute"] = attribute
        action["setpoint"]["delta_percent"] = delta_percent
        action["operation"] = direction

        # Build existing setpoints lookup
        existing_setpoints = {
            str(sp["id"]): sp
            for sp in action.get("setpoints") or []
            if sp.get("id") is not None
        }

        default_setpoint = action.get("setpoint") if isinstance(action.get("setpoint"), dict) else {}
        frozen_basis = cls._extract_frozen_basis(action)
        is_single_target = len(targets) == 1

        # Process each target
        setpoint_entries = []
        measurement_keys = []

        for target_id in targets:
            existing = existing_setpoints.get(str(target_id))

            # Determine measurement key
            measurement_key = cls.measurement_key(element_type, attribute, target_id)
            if existing and existing.get("measurement_key"):
                measurement_key = existing["measurement_key"]

            measurement_keys.append(measurement_key)

            # Determine basis value
            basis = cls._get_basis_value(
                target_id, existing, default_setpoint, frozen_basis,
                system_state, measurement_key, is_single_target
            )

            # Build setpoint entry
            entry = cls._build_setpoint_entry(
                target_id, attribute, delta_percent, basis,
                measurement_key, direction, element_type
            )
            setpoint_entries.append(entry)

        # Update action
        action["setpoints"] = setpoint_entries
        action["measurement_keys"] = [k for k in measurement_keys if k]

        cls._update_action_setpoint(action, setpoint_entries, action["measurement_keys"])
        cls._persist_frozen_basis(action, frozen_basis)

        return action
