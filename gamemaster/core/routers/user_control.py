"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

FastAPI routes for submitting and inspecting user-level control actions.

Endpoints declared here accept direct and cluster-based controls and
expose lightweight status inspection APIs.
"""

import logging

from fastapi import APIRouter, HTTPException

from ..domain.controllers.global_instances import get_user_control_manager
from ..entities.model import ControlInput, ClusterControlInput
from ..services.status_service import get_gamemaster_status

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)

router = APIRouter(tags=["User Control"])


@router.put("/control")
def user_control(control: ControlInput):
    """
    Receives a direct user control command, parses it for correct types,
    and stores it for later aggregation.
    """
    try:
        user_control_manager = get_user_control_manager()
        parsed_control = user_control_manager.parse_control(control.model_dump())
        result = user_control_manager.add_control(parsed_control)
        return result
    except Exception as e:
        logger.error("Error in user_control: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cluster_control")
def cluster_control(control: ClusterControlInput):
    """
    Receives a cluster-based user control command (dynamic or static clusters),
    parses it for correct types, and stores it for later aggregation.
    """
    try:
        user_control_manager = get_user_control_manager()
        parsed_control = user_control_manager.parse_cluster_control(control.dict())
        result = user_control_manager.add_cluster_control(parsed_control)
        return result
    except ValueError as ve:
        logger.error("ValueError in cluster_control: %s", str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Error in cluster_control: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/controls")
def get_next_step_controls():
    """Return user controls scheduled for the upcoming simulation step."""

    manager = get_user_control_manager()
    snapshot = manager.next_step_controls()
    controls = snapshot.get("controls", [])
    logger.debug(
        "Next-step user controls at %s: %s",
        snapshot.get("next_time"),
        controls,
    )
    return {
        "current_time": snapshot.get("current_time"),
        "time_step": snapshot.get("time_step"),
        "next_time": snapshot.get("next_time"),
        "controls": controls,
        "count": len(controls),
    }


@router.get("/status")
def user_status():
    """
    Retrieve current GameMaster service status and simulation metadata.

    Returns:
        dict: Status information assembled by `get_gamemaster_status`.
    """
    return get_gamemaster_status()
