"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

"""Time conversion helpers for the DSL engine."""


def to_seconds(value, unit):
    """
    Convert a time value to seconds based on the given unit.

    Args:
        value (float): The time value to convert.
        unit (str): The unit of the time value (e.g., 'seconds', 'minutes', 'hours').

    Returns:
        float: The time value in seconds.

    Raises:
        ValueError: If the unit is unknown.
    """
    unit = unit.lower()
    if unit in ["second", "seconds"]:
        return value
    elif unit in ["minute", "minutes"]:
        return value * 60
    elif unit in ["hour", "hours"]:
        return value * 3600
    else:
        raise ValueError(f"Unknown time unit: {unit}")
