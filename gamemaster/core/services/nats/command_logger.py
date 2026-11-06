"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Lightweight SQLite logger for NATS DSL command traffic.

Logging is best-effort; failures are swallowed to avoid blocking command delivery.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from typing import Any, Optional


logger = logging.getLogger(__name__)


class NATSCommandLogger:
    """Persist NATS command payloads to a local SQLite file."""

    def __init__(self, db_path: str, enabled: bool = True) -> None:
        self.db_path = db_path
        self.enabled = enabled
        if not self.enabled:
            return
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_db()
        logger.info("NATS DSL command logging enabled; writing to %s", self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dsl_command_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        simulation TEXT,
                        sim_time REAL,
                        subject TEXT NOT NULL,
                        source TEXT,
                        payload TEXT,
                        reply TEXT,
                        created_at REAL NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_dsl_command_logs_sim_time
                    ON dsl_command_logs(simulation, sim_time, created_at)
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.warning("Failed to initialize command log DB %s: %s", self.db_path, exc)

    @staticmethod
    def _to_json_blob(obj: Any) -> str:
        if obj is None:
            return ""
        if isinstance(obj, str):
            return obj
        try:
            return json.dumps(obj, default=str)
        except Exception:
            return str(obj)

    def _record_sync(
        self,
        *,
        simulation: Optional[str],
        sim_time: Optional[float],
        subject: str,
        source: Optional[str],
        payload: Any,
        reply: Any,
    ) -> None:
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO dsl_command_logs (
                        simulation, sim_time, subject, source,
                        payload, reply, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        simulation,
                        sim_time,
                        subject,
                        source,
                        self._to_json_blob(payload),
                        self._to_json_blob(reply),
                        time.time(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.debug("Failed to record NATS command log: %s", exc)

    async def record(
        self,
        *,
        simulation: Optional[str],
        sim_time: Optional[float],
        subject: str,
        source: Optional[str] = None,
        payload: Any = None,
        reply: Any = None,
    ) -> None:
        """Record a command or request/response payload.

        Args:
            simulation: Simulation name associated with the command.
            sim_time: Simulation time when the command was emitted.
            subject: NATS subject that carried the payload.
            source: Source label such as dsl/trainer/user.
            payload: Payload published or requested.
            reply: Optional reply payload for requests.
        """
        if not self.enabled:
            return
        if not simulation:
            return
        if not subject:
            return
        await asyncio.to_thread(
            self._record_sync,
            simulation=simulation,
            sim_time=sim_time,
            subject=subject,
            source=source,
            payload=payload,
            reply=reply,
        )


__all__ = ["NATSCommandLogger"]
