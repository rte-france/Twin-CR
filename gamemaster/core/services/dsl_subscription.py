"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Helpers to trigger DSL measurement subscriptions outside the bridge loop.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from . import get_nats_bridge


logger = logging.getLogger(__name__)


async def ensure_measurements_subscribed(
    measurement_keys: Iterable[str],
    *,
    simulation_name: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Ask the NATS bridge to subscribe to the provided measurement keys."""

    bridge = get_nats_bridge()
    if bridge is None:
        logger.debug("Skipping eager subscription; NATS bridge not ready")
        return

    base_metadata = dict(metadata or {})
    if simulation_name and "simulation" not in base_metadata:
        base_metadata["simulation"] = simulation_name

    for key in dict.fromkeys(k for k in measurement_keys if k):
        try:
            await bridge.ensure_measurement_subscription(key, base_metadata)
        except Exception:  # pragma: no cover - best effort logging
            logger.debug("Failed to ensure subscription for %s", key, exc_info=True)


__all__ = ["ensure_measurements_subscribed"]
