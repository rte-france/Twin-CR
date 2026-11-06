"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Shared helpers for reporting GameMaster simulation status.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from ..domain.controllers.global_instances import get_simulation_controller
from ..utils.clock import get_current_time
from ..utils.clickhouse_client import get_clickhouse_client
from .nats.health import nats_health_check


logger = logging.getLogger(__name__)


def _safe_float(value, default: float = 0.0) -> float:
    """
    Attempt to convert a value to float while providing a default fallback.

    Args:
        value: Value to convert.
        default (float): Value returned when conversion fails.

    Returns:
        float: Numeric value or fallback.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _check_storage_health() -> str:
    """
    Verify that the storage backend is reachable.

    Returns:
        str: ``healthy`` when accessible, ``unavailable`` otherwise.
    """
    try:
        client = get_clickhouse_client()
        if client.check_bucket_exists(client.bucket_name):
            return "healthy"
        return "unavailable"
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Storage health check failed: %s", exc)
        return "unavailable"


def get_gamemaster_status(
    nats_healthy: Optional[bool] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Produce a status summary covering simulation and infrastructure health.

    Args:
        nats_healthy (Optional[bool]): Precomputed NATS status to avoid
            duplicate checks; when ``None`` a fresh health check runs.

    Returns:
        Dict[str, Dict[str, str]]: Simulation state and service statuses.
    """
    simulation_controller = get_simulation_controller()
    interpreter = simulation_controller.interpreter if simulation_controller else None
    status = "not_ready"
    simulation_name = (
        simulation_controller.simulation_name if simulation_controller else None
    )
    clock_time = (
        _safe_float(get_current_time(simulation_name)) if simulation_name else 0.0
    )

    if interpreter:
        interpreter_time = _safe_float(getattr(interpreter, "current_time", 0.0))
        current = max(clock_time, interpreter_time)
        duration = _safe_float(getattr(interpreter, "duration", 0.0))
        if current <= 0.0:
            status = "ready"
        elif duration and current >= duration:
            status = "completed"
        else:
            status = "running"

    return {
        "simulation": {
            "name": simulation_name,
            "status": status,
        },
        "services": {
            "nats": (
                "healthy"
                if (nats_healthy if nats_healthy is not None else nats_health_check())
                else "unhealthy"
            ),
            "storage": _check_storage_health(),
        },
    }


def get_simulation_metadata() -> Optional[Dict[str, object]]:
    """
    Return metadata describing the currently loaded simulation.

    Returns:
        Optional[Dict[str, object]]: Simulator name, IIDM artifact, timing
        info, and DSL file path; ``None`` when not initialized.
    """
    simulation_controller = get_simulation_controller()
    interpreter = simulation_controller.interpreter if simulation_controller else None
    if interpreter is None:
        return None

    simulation_name = (
        simulation_controller.simulation_name if simulation_controller else None
    )
    clock_time = (
        _safe_float(get_current_time(simulation_name)) if simulation_name else 0.0
    )
    interpreter_time = _safe_float(getattr(interpreter, "current_time", 0.0))

    metadata: Dict[str, object] = {
        "simulation": simulation_name,
        "dsl_file": getattr(simulation_controller, "dsl_filename", None),
        "iidm_artifact": getattr(simulation_controller, "iidm_artifact_id", None)
        or getattr(interpreter, "artifact_id", None),
        "time_step": _safe_float(getattr(interpreter, "time_step", 0.0)) or None,
        "total_duration": _safe_float(getattr(interpreter, "duration", 0.0)) or None,
        "time_passed": max(clock_time, interpreter_time),
    }

    return metadata


__all__ = ["get_gamemaster_status", "get_simulation_metadata"]
