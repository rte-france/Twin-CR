"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Utilities for performing NATS health checks.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os

import nats.aio.msg
from nats.aio.client import Client as NATS


logger = logging.getLogger(__name__)


async def roundtrip_with_client(nc: NATS, timeout: float = 1.0) -> bool:
    """Verify publish/subscribe using an existing NATS client."""

    inbox = nc.new_inbox()
    event = asyncio.Event()

    async def _handler(
        msg: nats.aio.msg.Msg,
    ) -> None:  # pragma: no cover - trivial callback
        """Signal receipt of the published probe message."""
        event.set()

    sid = await nc.subscribe(inbox, cb=_handler)
    try:
        await nc.publish(inbox, b"gm-health-probe")
        await nc.flush(timeout=timeout)
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("NATS client roundtrip failed: %s", exc)
        return False
    finally:
        with contextlib.suppress(Exception):
            await nc.unsubscribe(sid)


async def _roundtrip_new_client(nats_url: str, timeout: float = 1.0) -> bool:
    """
    Create a temporary NATS client and perform a health round trip.

    Args:
        nats_url (str): URL for the NATS server.
        timeout (float): Time allowed for connection and round trip.

    Returns:
        bool: True when the publish/subscribe sequence succeeds.
    """
    nc = NATS()
    try:
        await nc.connect(nats_url)
        success = await roundtrip_with_client(nc, timeout=timeout)
        return success
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("NATS health check connection failed: %s", exc)
        return False
    finally:
        with contextlib.suppress(Exception):
            await nc.close()


def nats_health_check(timeout: float = 1.0) -> bool:
    """Synchronous helper that creates a temporary connection and verifies pub/sub."""

    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    try:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                _roundtrip_new_client(nats_url, timeout=timeout)
            )
        finally:
            loop.close()
    except Exception as exc:  # pragma: no cover - best effort
        logger.debug("NATS health check failed: %s", exc)
        return False


__all__ = ["nats_health_check", "roundtrip_with_client"]
