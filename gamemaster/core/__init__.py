"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Wire GameMaster routers and supporting services into the FastAPI app.

This module exposes helper functions that attach the API routes and
start the background services required by the simulator ecosystem.
"""

from .routers import trainer, sim_control, user_control, iidm_control, autocomplete
from .routers import queue as queue_router
from .routers import atomic as atomic_router
from .routers import logs as logs_router
from .services import setup_gamemaster_services


def setup_game_master_routes(app):
    """
    Register all GameMaster routers with the provided FastAPI app.

    Args:
        app (fastapi.FastAPI): Application instance that exposes the
            trainer, simulator, user control, IIDM, queue, and atomic
            update endpoints.
    """
    app.include_router(trainer.router, prefix="/trainer", tags=["Trainer"])
    app.include_router(sim_control.router, prefix="/sim", tags=["Simulator Control"])
    app.include_router(user_control.router, prefix="/user", tags=["User Control"])
    app.include_router(iidm_control.router, prefix="/iidm", tags=["IIDM Control"])
    app.include_router(autocomplete.router, prefix="/lsp", tags=["Autocomplete"])
    app.include_router(queue_router.router, prefix="/queue", tags=["Event Store"])
    app.include_router(logs_router.router, prefix="/logs", tags=["DSL Command Logs"])
    # Separate, top-level atomic update endpoint for next-step DSL editing
    app.include_router(atomic_router.router, prefix="/atomic", tags=["Atomic Update"])


def initialize_game_master_services(app):
    """
    Start background services after the FastAPI application is created.

    Args:
        app (fastapi.FastAPI): Application container whose state is
            injected into the service initialization pipeline.
    """
    setup_gamemaster_services(app)
