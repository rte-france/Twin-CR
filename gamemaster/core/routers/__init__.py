"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Expose FastAPI routers for trainer, simulator-control, and user-control.

This module simplifies discovery for consumers that want to import all
router objects from a single location.
"""

from .trainer import router as trainer_router
from .sim_control import router as sim_router
from .user_control import router as user_router
from .autocomplete import router as autocomplete_router

__all__ = ["trainer_router", "sim_router", "user_router", "autocomplete_router"]
