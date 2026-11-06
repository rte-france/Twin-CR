"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Provide utilities to map symbolic control actions to numeric values.

The resolver merges defaults, configuration files, constructor input,
and environment overrides so simulator controls can be expressed in a
consistent numeric format.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional


logger = logging.getLogger(__name__)


def _safe_merge(
    base: Dict[str, Dict[str, float]], updates: Optional[Dict[str, Dict[str, float]]]
):
    """
    Merge nested control mappings without mutating the original dicts.

    Args:
        base (Dict[str, Dict[str, float]]): Existing mapping used as the
            template for results.
        updates (Optional[Dict[str, Dict[str, float]]]): Optional
            overlay mapping whose nested entries take precedence.

    Returns:
        Dict[str, Dict[str, float]]: Combined mapping containing deep
            copies of ``base`` data with ``updates`` applied.
    """
    if not updates:
        return base
    merged = {ctype: actions.copy() for ctype, actions in base.items()}
    for control_type, mapping in updates.items():
        if not isinstance(mapping, dict):
            logger.warning(
                "Ignoring invalid mapping for control type %s: %s",
                control_type,
                mapping,
            )
            continue
        merged.setdefault(control_type, {}).update(mapping)
    return merged


DEFAULT_CONFIG_FILE = (
    Path(__file__).resolve().parents[2] / "config" / "control_value_map.json"
)


class ControlValueResolver:
    """Utility to convert control actions into numeric values.

    The resolver merges defaults with optional configuration supplied through
    the ``mapping`` constructor argument, the ``CONTROL_VALUE_MAP`` environment
    variable, and JSON files on disk.

    Example mapping:

    .. code-block:: json

        {
            "switch": {"open": 0, "close": 1},
            "breaker": {"open": 0, "close": 1}
        }
    """

    DEFAULT_MAPPING: Dict[str, Dict[str, float]] = {
        "switch": {"open": 0, "close": 1},
        "line": {"open": 0, "close": 1},
    }

    def __init__(
        self,
        mapping: Optional[Dict[str, Dict[str, float]]] = None,
        env_var: str = "CONTROL_VALUE_MAP",
        config_path: Optional[Path] = None,
    ):
        """
        Initialize the resolver by loading mappings from every source.

        Args:
            mapping (Optional[Dict[str, Dict[str, float]]]): Explicit
                mappings provided by the caller.
            env_var (str): Name of the environment variable that may
                contain JSON overrides.
            config_path (Optional[pathlib.Path]): Optional path to a
                JSON document on disk used for defaults.
        """
        config_mapping = self._load_from_file(config_path or DEFAULT_CONFIG_FILE)
        env_mapping = self._load_from_env(env_var)
        base = {
            ctype: actions.copy() for ctype, actions in self.DEFAULT_MAPPING.items()
        }
        if config_mapping:
            base = _safe_merge(base, config_mapping)
        if mapping:
            base = _safe_merge(base, mapping)
        if env_mapping:
            base = _safe_merge(base, env_mapping)
        self._mapping = base

    def _load_from_file(self, path: Path) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Load a control mapping from the provided JSON file.

        Args:
            path (pathlib.Path): Location of the config file.

        Returns:
            Optional[Dict[str, Dict[str, float]]]: Parsed mapping when
            the file exists and is valid, otherwise ``None``.
        """
        try:
            if not path.exists():
                return None
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("Control mapping file must contain a JSON object")
            normalized = {}
            for control_type, entries in data.items():
                if not isinstance(entries, dict):
                    logger.warning(
                        "Skipping non-object mapping for %s in %s", control_type, path
                    )
                    continue
                normalized[control_type] = entries
            logger.debug("Loaded control value mapping from %s", path)
            return normalized
        except Exception as exc:
            logger.warning("Failed to load control mapping file %s: %s", path, exc)
            return None

    def _load_from_env(self, env_var: str) -> Optional[Dict[str, Dict[str, float]]]:
        """
        Parse a nested control mapping from an environment variable.

        Args:
            env_var (str): Name of the environment variable that may
                contain a JSON encoded mapping.

        Returns:
            Optional[Dict[str, Dict[str, float]]]: Normalized mapping or
            ``None`` when the variable is unset or invalid.
        """
        payload = os.getenv(env_var)
        if not payload:
            return None
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError("Top-level control mapping must be a JSON object")
            # Ensure nested dicts
            normalized = {}
            for control_type, entries in data.items():
                if not isinstance(entries, dict):
                    logger.warning("Skipping non-object mapping for %s", control_type)
                    continue
                normalized[control_type] = entries
            return normalized
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", env_var, exc)
            return None

    def resolve(self, control_type: str, action: str) -> Optional[float]:
        """
        Convert a symbolic control type/action pair into a numeric value.

        Args:
            control_type (str): Control category such as ``switch`` or
                ``generator``.
            action (str): Operation name to resolve within the category.

        Returns:
            Optional[float]: Configured numeric mapping, or ``None`` if
            no mapping exists.
        """
        control_key = str(control_type or "").lower()
        action_key = str(action or "").lower()
        mapping = self._mapping.get(control_key, {})
        value = mapping.get(action_key)
        if value is None:
            logger.debug("No numeric mapping for %s/%s", control_key, action_key)
        return value

    def set_mapping(self, control_type: str, action: str, value: float) -> None:
        """
        Persist a single control/action mapping in the resolver cache.

        Args:
            control_type (str): Category name to update.
            action (str): Action label to normalize.
            value (float): Numeric representation associated with the
                action.
        """
        control_key = str(control_type or "").lower()
        action_key = str(action or "").lower()
        self._mapping.setdefault(control_key, {})[action_key] = value

    def update_control(self, control_type: str, mapping: Dict[str, float]) -> None:
        """
        Overlay multiple action mappings for a control type at once.

        Args:
            control_type (str): Target category to update.
            mapping (Dict[str, float]): Actions and numeric values.
        """
        control_key = str(control_type or "").lower()
        self._mapping.setdefault(control_key, {}).update(
            {str(k).lower(): v for k, v in mapping.items()}
        )

    def get_mapping(self) -> Dict[str, Dict[str, float]]:
        """
        Return a defensive copy of the current control mapping.

        Returns:
            Dict[str, Dict[str, float]]: Per-type dictionaries describing
            the stored numeric translations.
        """
        return {ctype: actions.copy() for ctype, actions in self._mapping.items()}
