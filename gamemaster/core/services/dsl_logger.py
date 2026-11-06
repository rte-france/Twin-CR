"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

SQLite-backed logger that captures DSL text fragments for replaying simulations.

The logger stores the base DSL script loaded at initialization as well as any
trainer or user DSL snippets appended during a run. Entries are timestamped so
clients can reconstruct an updated DSL program that reflects runtime edits.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from typing import Any, Optional


class DSLExecutionLogger:
    """Persist DSL snippets and metadata for later retrieval."""

    def __init__(self, db_path: str, enabled: bool = True) -> None:
        self.db_path = db_path
        self.enabled = enabled
        if not self.enabled:
            return
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS dsl_execution_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    source TEXT,
                    sim_time REAL,
                    dsl_text TEXT,
                    metadata TEXT,
                    event_id TEXT,
                    status TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dsl_execution_log_simulation
                ON dsl_execution_log (simulation, created_at)
                """
            )
            self._ensure_columns(cur)
            conn.commit()

    @staticmethod
    def _ensure_columns(cur: sqlite3.Cursor) -> None:
        cur.execute("PRAGMA table_info(dsl_execution_log)")
        cols = {row[1] for row in cur.fetchall()}
        required = {
            "event_id": "TEXT",
            "status": "TEXT",
        }
        for name, definition in required.items():
            if name not in cols:
                cur.execute(
                    f"ALTER TABLE dsl_execution_log ADD COLUMN {name} {definition}"
                )

    @staticmethod
    def _json_blob(value: Any | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, default=str)
        except Exception:
            return str(value)

    def _record_sync(
        self,
        *,
        simulation: str,
        entry_type: str,
        source: Optional[str],
        dsl_text: Optional[str],
        sim_time: Optional[float],
        metadata: Any | None,
        event_id: Optional[str],
        status: Optional[str],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dsl_execution_log (
                    simulation, entry_type, source, sim_time, dsl_text, metadata,
                    event_id, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    simulation,
                    entry_type,
                    source,
                    sim_time,
                    dsl_text,
                    self._json_blob(metadata),
                    event_id,
                    status,
                    time.time(),
                ),
            )
            conn.commit()

    async def record_entry(
        self,
        *,
        simulation: Optional[str],
        entry_type: str,
        source: Optional[str],
        dsl_text: Optional[str],
        sim_time: Optional[float] = None,
        metadata: Any | None = None,
        event_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> None:
        if not self.enabled or not simulation:
            return
        await asyncio.to_thread(
            self._record_sync,
            simulation=simulation,
            entry_type=entry_type,
            source=source,
            dsl_text=dsl_text,
            sim_time=sim_time,
            metadata=metadata,
            event_id=event_id,
            status=status,
        )

    def _reset_simulation_sync(self, simulation: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM dsl_execution_log WHERE simulation = ?", (simulation,)
            )
            conn.commit()

    async def reset_simulation(self, simulation: Optional[str]) -> None:
        if not self.enabled or not simulation:
            return
        await asyncio.to_thread(self._reset_simulation_sync, simulation)

    async def record_base_script(
        self,
        *,
        simulation: Optional[str],
        dsl_text: str,
        metadata: Any | None = None,
    ) -> None:
        if not self.enabled or not simulation:
            return
        await self.reset_simulation(simulation)
        await self.record_entry(
            simulation=simulation,
            entry_type="base_script",
            source="dsl",
            dsl_text=dsl_text,
            sim_time=0.0,
            metadata=metadata,
            event_id=None,
            status="recorded",
        )

    async def record_append(
        self,
        *,
        simulation: Optional[str],
        source: str,
        dsl_text: str,
        sim_time: Optional[float] = None,
        metadata: Any | None = None,
    ) -> None:
        await self.record_entry(
            simulation=simulation,
            entry_type="append",
            source=source,
            dsl_text=dsl_text,
            sim_time=sim_time,
            metadata=metadata,
            event_id=None,
            status="recorded",
        )

    async def record_execution_result(
        self,
        *,
        simulation: Optional[str],
        event_id: Optional[str],
        succeeded: bool,
        sim_time: Optional[float] = None,
        metadata: Any | None = None,
        dsl_text: Optional[str] = None,
    ) -> None:
        status = "executed" if succeeded else "failed"
        meta = dict(metadata or {})
        meta.setdefault("event_id", event_id)
        await self.record_entry(
            simulation=simulation,
            entry_type="execution",
            source="gamemaster",
            dsl_text=dsl_text,
            sim_time=sim_time,
            metadata=meta,
            event_id=event_id,
            status=status,
        )


__all__ = ["DSLExecutionLogger"]
