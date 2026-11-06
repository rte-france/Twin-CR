"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Thread-safe cache for latest measurement values received via NATS.
"""

from __future__ import annotations

from threading import Lock
from typing import Dict


_lock = Lock()
_values: Dict[str, float] = {}


def update_value(key: str, value: float) -> None:
    """
    Record the most recent numeric value for a measurement key.

    Args:
        key (str): Measurement identifier.
        value (float): Latest reading to store.
    """
    key = (key or "").strip()
    if not key:
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return
    with _lock:
        _values[key] = numeric


def snapshot() -> Dict[str, float]:
    """
    Return a copy of the cached measurement values.

    Returns:
        Dict[str, float]: Mapping from measurement key to latest value.
    """
    with _lock:
        return _values.copy()


def clear() -> None:
    """Reset the cache, removing every stored value."""
    with _lock:
        _values.clear()


__all__ = ["update_value", "snapshot", "clear"]
