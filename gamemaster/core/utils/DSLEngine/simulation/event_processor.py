"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

from typing import Optional


def apply_interval_law(
    *,
    action: dict,
    base_action: dict,
    law: Optional[str],
    start: Optional[float],
    end: Optional[float],
    current_time: float,
    time_step: Optional[float],
) -> bool:
    if not isinstance(action, dict):
        return True
    if not law:
        return True
    law_normalized = str(law).strip().lower()
    if law_normalized != "linear":
        return True
    if start is None or end is None or end <= start:
        return False

    span = end - start
    if span <= 0:
        return False
    total_percent = None
    if isinstance(base_action, dict):
        total_percent = base_action.get("percentage")
        if total_percent is None:
            total_percent = base_action.get("setpoint", {}).get("delta_percent")
    if total_percent is None:
        return True
    try:
        total_percent = float(total_percent)
    except (TypeError, ValueError):
        return True

    step_seconds = time_step if time_step and time_step > 0 else span
    steps = max(1, int(round(span / step_seconds)))
    step_increment = total_percent / float(steps)

    elapsed = current_time - start
    if elapsed < 0:
        applied_steps = 0
    else:
        applied_steps = min(steps, int(round(elapsed / step_seconds)))

    current_percent = step_increment * applied_steps

    action["percentage"] = current_percent
    if isinstance(action.get("setpoint"), dict):
        action["setpoint"]["delta_percent"] = current_percent

    return applied_steps < steps
