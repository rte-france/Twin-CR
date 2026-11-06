"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Expose FastAPI router utilities for orchestrator-specific endpoints.

The helpers declared here wire the Master coordinator into dependency
injection and lifecycle events without altering the coordinator logic.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends
from ..coordinator import Master


# Function to get the Master instance for dependency injection
def get_master_instance():
    """
    Return the configured `Master` dependency placeholder.

    The application overrides this dependency at startup, so the
    function body intentionally does nothing until the override is set.
    """
    # This function will be replaced by app.dependency_overrides
    pass


async def initialize_master(master_instance):
    """Initialize the Master instance with necessary configurations."""
    try:
        # Asynchronous initialization if needed
        # For example, loading data at startup
        logging.info("Initializing Master orchestrator...")

        # If master needs to be started in a non-blocking way
        asyncio.create_task(run_master_async(master_instance))

        logging.info("Master orchestrator initialized successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to initialize Master orchestrator: {str(e)}")
        return False


async def run_master_async(master_instance):
    """Run master.run() asynchronously."""
    try:
        # If the run() method is blocking, you can execute it in a separate thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, master_instance.run)
    except Exception as e:
        logging.error(f"Error running Master: {str(e)}")


def setup_orchestrator_routes(app, master):
    """Configure orchestrator routes and initialize the Master instance."""

    # Dependency injection configuration
    app.dependency_overrides[get_master_instance] = lambda: master

    # Include router with defined routes

    # Startup event to initialize Master
    @app.on_event("startup")
    async def startup_event():
        """Start the Master orchestrator when the FastAPI app boots."""
        await initialize_master(master)

    # You can add other events like cleanup if needed
    @app.on_event("shutdown")
    async def shutdown_event():
        """Log orchestrator shutdown so operators can trace lifecycles."""
        # Cleanup or proper shutdown of the Master instance if needed
        logging.info("Shutting down Master orchestrator...")
