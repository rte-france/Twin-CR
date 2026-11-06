"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Shared helpers to scale interval actions based on their law definition.
"""

from __future__ import annotations

import logging
import math
from typing import Optional


logger = logging.getLogger(__name__)


def apply_interval_law_scaling(
    container: dict, current_time: float, time_step: Optional[float]
) -> None:
    """Mutate an interval action container in-place to reflect law-based scaling."""

    if not isinstance(container, dict):
        return

    action = container.get("action")
    if not isinstance(action, dict):
        return

    law = str(container.get("law") or "").strip().lower()
    if law != "linear":
        return

    start = container.get("interval_start")
    end = container.get("interval_end")
    if start is None or end is None:
        return
    try:
        start = float(start)
        end = float(end)
    except (TypeError, ValueError):
        return
    if end <= start:
        return

    step_seconds = time_step if time_step and time_step > 0 else (end - start)
    if step_seconds <= 0:
        step_seconds = end - start
    if step_seconds <= 0:
        return

    steps = max(1, int(math.ceil((end - start) / step_seconds)))
    elapsed = current_time - start
    if elapsed < 0:
        applied_steps = 0
    else:
        applied_steps = int(max(0, min(steps, (elapsed / step_seconds) + 1e-9)))

    ratio = applied_steps / steps if steps else 0.0

    action_type = str(action.get("type") or "").lower()
    operation = str(action.get("operation") or "").lower()
    if operation == "set" or action_type.startswith("set_"):
        def _coerce(value):
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        setpoint = action.get("setpoint") if isinstance(action.get("setpoint"), dict) else {}
        sp_target = _coerce(setpoint.get("target_value"))
        sp_from = _coerce(setpoint.get("from_value"))

        setpoints = action.get("setpoints") or []
        if setpoints:
            updated = []
            for idx, entry in enumerate(setpoints):
                if not isinstance(entry, dict):
                    continue
                target = _coerce(entry.get("target_value"))
                if target is None:
                    target = sp_target
                if target is None:
                    target = _coerce(entry.get("absolute_value"))
                if target is not None and entry.get("target_value") is None:
                    entry["target_value"] = target

                from_value = _coerce(entry.get("from_value"))
                if from_value is None:
                    if isinstance(setpoint.get("from_values"), list) and idx < len(setpoint["from_values"]):
                        from_value = _coerce(setpoint["from_values"][idx])
                    if from_value is None:
                        from_value = sp_from
                if from_value is not None and entry.get("from_value") is None:
                    entry["from_value"] = from_value

                if from_value is None or target is None:
                    updated.append(entry.get("absolute_value"))
                    continue

                current_value = from_value + (target - from_value) * ratio
                entry["absolute_value"] = current_value
                updated.append(current_value)

            if len(setpoints) == 1 and isinstance(setpoints[0], dict):
                action["setpoint"].update(
                    {
                        "absolute_value": setpoints[0].get("absolute_value"),
                        "target_value": setpoints[0].get("target_value"),
                        "from_value": setpoints[0].get("from_value"),
                    }
                )
            elif updated:
                action["setpoint"].update(
                    {
                        "absolute_values": updated,
                        "target_values": [
                            sp.get("target_value")
                            for sp in setpoints
                            if isinstance(sp, dict)
                        ],
                        "from_values": [
                            sp.get("from_value")
                            for sp in setpoints
                            if isinstance(sp, dict)
                        ],
                    }
                )
        else:
            target = sp_target
            if target is None:
                target = _coerce(setpoint.get("absolute_value"))
            if target is not None and setpoint.get("target_value") is None:
                setpoint["target_value"] = target

            from_value = sp_from
            if from_value is None:
                from_value = _coerce(setpoint.get("from_values"))
            if from_value is not None and setpoint.get("from_value") is None:
                setpoint["from_value"] = from_value

            if from_value is None or target is None:
                return
            setpoint["absolute_value"] = from_value + (target - from_value) * ratio

        return

    total_percent = action.get("target_percentage")
    if total_percent is None:
        total_percent = action.get("percentage")
    if total_percent is None:
        return
    try:
        total_percent = float(total_percent)
    except (TypeError, ValueError):
        return

    current_percent = total_percent * ratio

    action["target_percentage"] = total_percent
    action["percentage"] = current_percent

    setpoint = action.get("setpoint")
    if isinstance(setpoint, dict):
        setpoint["delta_percent"] = current_percent
    for entry in action.get("setpoints") or []:
        if isinstance(entry, dict):
            entry["delta_percent"] = current_percent
