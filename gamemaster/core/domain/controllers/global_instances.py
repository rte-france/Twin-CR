"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Provide memoized singleton-style access to frequently used controllers.

The helpers ensure expensive dependencies such as the event store,
simulation controller, and control-value resolver are constructed once
per process and reused throughout the FastAPI application.
"""

from functools import lru_cache

from .control_value_resolver import ControlValueResolver
from .scn_controller import SimulationController
from .user_controller import UserControlManager
from ..event_store import EventStore


@lru_cache(maxsize=1)
def get_event_store() -> EventStore:
    """
    Instantiate and cache the domain event store.

    Returns:
        EventStore: Persistent event-store facade reused across requests.
    """
    return EventStore()


@lru_cache(maxsize=1)
def get_simulation_controller() -> SimulationController:
    """
    Build a cached simulation controller wired to the event store.

    Returns:
        SimulationController: Object that orchestrates DSL execution and
        simulator coordination.
    """
    return SimulationController(event_store=get_event_store())


@lru_cache(maxsize=1)
def get_user_control_manager() -> UserControlManager:
    """
    Create a singleton user-control manager sharing global resources.

    Returns:
        UserControlManager: Controller that tracks control submissions
        and ensures they are synchronized with simulations.
    """
    return UserControlManager(
        get_simulation_controller(), event_store=get_event_store()
    )


@lru_cache(maxsize=1)
def get_control_value_resolver() -> ControlValueResolver:
    """
    Lazily allocate a control-value resolver with default mappings.

    Returns:
        ControlValueResolver: Resolver capable of translating symbolic
        control actions into numeric values.
    """
    return ControlValueResolver()


__all__ = [
    "get_event_store",
    "get_simulation_controller",
    "get_user_control_manager",
    "get_control_value_resolver",
]
