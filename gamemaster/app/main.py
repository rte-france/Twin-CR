"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Initialize the GameMaster FastAPI application and supporting services.

The module configures logging, attaches middleware, registers routers,
and ensures background services are started when the app is imported.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gamemaster.core import (
    initialize_game_master_services,
    setup_game_master_routes,
)


def _configure_logging() -> logging.Logger:
    """Configure logging once and share the resulting logger."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("gamemaster-api")
    logger.info("Configured logging level: %s", level_name)
    return logger


logger = _configure_logging()

app = FastAPI(
    title="GameMaster API",
    description="GameMaster control and simulation API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_game_master_routes(app)
initialize_game_master_services(app)
