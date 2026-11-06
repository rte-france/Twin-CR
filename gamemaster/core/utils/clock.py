"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Track monotonic simulation clocks shared between API components.

This module ensures the clock never regresses and supports per-simulation
reset semantics when orchestrators restart.
"""

from typing import Dict
import threading
import logging


class ClockRegressionError(ValueError):
    """Raised when a simulation clock attempts to move backwards."""


_lock = threading.Lock()
_current_time_by_sim: Dict[str, float] = {}
_pending_reset_by_sim: Dict[str, float] = {}
_RESET_ACCEPT_THRESHOLD = 5.0  # seconds
_logger = logging.getLogger(__name__)


def _normalize_simulation_key(simulation: str | None) -> str:
    """
    Map a simulation identifier to a stable key used in dictionaries.

    Args:
        simulation (Optional[str]): Simulation name provided by callers.

    Returns:
        str: ``"default"`` when no simulation is provided, otherwise the name.
    """
    return "default" if simulation is None else simulation


def set_current_time(simulation: str | None, t: float) -> None:
    """Record the current simulation time, enforcing a non-decreasing clock."""
    key = _normalize_simulation_key(simulation)
    new_time = float(t)
    with _lock:
        reset_previous = _pending_reset_by_sim.get(key)
        if reset_previous is not None:
            accept_limit = max(_RESET_ACCEPT_THRESHOLD, reset_previous - 1e-6)
            if new_time <= accept_limit:
                _pending_reset_by_sim.pop(key, None)
                _current_time_by_sim[key] = new_time
                return
            if new_time >= reset_previous:
                _logger.debug(
                    "Ignoring time %s for simulation '%s' while waiting for restart below %s.",
                    new_time,
                    key,
                    reset_previous,
                )
                return
        prev_time = _current_time_by_sim.get(key)
        if prev_time is not None and new_time < prev_time:
            message = f"Received time {new_time} before last confirmed time {prev_time} for simulation '{key}'."
            _logger.warning(message)
            raise ClockRegressionError(message)
        _current_time_by_sim[key] = new_time


def get_current_time(simulation: str | None) -> float:
    """
    Retrieve the last known simulation time.

    Args:
        simulation (Optional[str]): Simulation name.

    Returns:
        float: Time recorded via `set_current_time` or ``0.0``.
    """
    key = _normalize_simulation_key(simulation)
    with _lock:
        return float(_current_time_by_sim.get(key, 0.0))


def reset_clock(simulation: str | None = None) -> None:
    """Reset stored time for a simulation (or all simulations if None)."""
    with _lock:
        if simulation is None:
            _current_time_by_sim.clear()
            _pending_reset_by_sim.clear()
        else:
            key = _normalize_simulation_key(simulation)
            previous = _current_time_by_sim.pop(key, None)
            if previous is not None:
                _pending_reset_by_sim[key] = previous
            else:
                _pending_reset_by_sim.pop(key, None)
