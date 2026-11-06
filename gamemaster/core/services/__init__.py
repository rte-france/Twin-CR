"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Service layer helpers for the Game Master feature.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os

from fastapi import FastAPI

from .simulator_control_service import (
    SimulationNotInitializedError,
    compute_simulator_control_commands,
)
from .status_service import get_gamemaster_status, get_simulation_metadata
from .nats.bridge import GameMasterNATSBridge
from .dsl_logger import DSLExecutionLogger
from .dsl_logging import set_dsl_logger
from .nats.command_logger import NATSCommandLogger


logger = logging.getLogger(__name__)

_nats_bridge: GameMasterNATSBridge | None = None
_bridge_connect_task: asyncio.Task | None = None


def get_nats_bridge() -> GameMasterNATSBridge | None:
    """Return the active NATS bridge instance if it has connected."""

    return _nats_bridge


def setup_gamemaster_services(app: FastAPI) -> None:
    """Attach startup/shutdown handlers for GameMaster background services."""

    nats_enabled = os.getenv("NATS_BRIDGE_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    log_enabled = os.getenv("DSL_COMMAND_LOG_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    log_db_path = os.getenv("DSL_COMMAND_LOG_DB_PATH", "data/dsl_command_logs.db")

    dsl_logger = (
        DSLExecutionLogger(db_path=log_db_path, enabled=log_enabled)
        if log_enabled
        else None
    )
    set_dsl_logger(dsl_logger)
    command_logger = (
        NATSCommandLogger(db_path=log_db_path, enabled=log_enabled)
        if log_enabled
        else None
    )

    @app.on_event("startup")
    async def start_gamemaster_bridge() -> (
        None
    ):  # pragma: no cover - integration wiring
        """Start the NATS bridge connection task during application boot."""
        if not nats_enabled:
            logger.info("GameMaster NATS bridge disabled via environment variable")
            return

        global _nats_bridge, _bridge_connect_task  # pylint: disable=global-statement
        if _nats_bridge is not None:
            return
        bridge = GameMasterNATSBridge(
            nats_url=nats_url,
            command_logger=command_logger,
        )
        _nats_bridge = bridge
        logger.info("GameMaster NATS bridge targeting %s", nats_url)

        async def connect_with_retry() -> None:
            """
            Attempt to connect the NATS bridge with exponential backoff.

            The coroutine keeps retrying until the bridge connects or the
            task is cancelled during application shutdown.
            """
            delay = 1.0
            while True:
                try:
                    await bridge.connect()
                    logger.info("GameMaster NATS bridge connected")
                    global _bridge_connect_task  # pylint: disable=global-statement
                    _bridge_connect_task = None
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover
                    logger.warning(
                        "Failed to connect GameMaster NATS bridge to %s: %s",
                        nats_url,
                        exc,
                    )
                    with contextlib.suppress(Exception):
                        await bridge.close()
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 30.0)

        _bridge_connect_task = asyncio.create_task(connect_with_retry())

    @app.on_event("shutdown")
    async def stop_gamemaster_bridge() -> None:  # pragma: no cover
        """Cancel any pending connection tasks and close the NATS bridge."""
        global _nats_bridge, _bridge_connect_task  # pylint: disable=global-statement
        if _bridge_connect_task is not None:
            _bridge_connect_task.cancel()
            try:
                await _bridge_connect_task
            except asyncio.CancelledError:
                pass
            _bridge_connect_task = None
        bridge = _nats_bridge
        if bridge is None:
            return
        try:
            await bridge.close()
            logger.info("GameMaster NATS bridge stopped on application shutdown")
        finally:
            _nats_bridge = None


__all__ = [
    "SimulationNotInitializedError",
    "compute_simulator_control_commands",
    "get_gamemaster_status",
    "get_simulation_metadata",
    "get_nats_bridge",
    "setup_gamemaster_services",
]
