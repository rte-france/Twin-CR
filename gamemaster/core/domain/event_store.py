"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Provide a lightweight SQLite-backed event store for GameMaster.

The implementation emphasizes predictable schemas, idempotent inserts,
and helper routines for promoting, rescheduling, and summarizing events.
"""

import os
import re
import sqlite3
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

import orjson

_TAGGED_DSL_RE = re.compile(r'\btagged\s+"([^"]+)"', re.IGNORECASE)


class EventStore:
    """
    Minimal, file-backed event store for GameMaster events.

    - Provides persistence for DSL and user events
    - Append-only with basic status transitions
    - Designed to be a non-breaking, incremental addition
    """

    def __init__(self, db_path: str = "data/game_master_events.db") -> None:
        """
        Initialize the event store and ensure the database schema exists.

        Args:
            db_path (str): Path to the SQLite database file; accepts
                ``:memory:`` for ephemeral stores.
        """
        self.db_path = db_path
        # Create parent directory only when a real filesystem path is provided
        parent = os.path.dirname(self.db_path)
        if self.db_path != ":memory:" and parent:
            os.makedirs(parent, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """
        Open a new SQLite connection configured for row access.

        Returns:
            sqlite3.Connection: Connection whose ``row_factory`` produces
            ``sqlite3.Row`` objects.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create the events table and supporting indexes when absent."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    type TEXT NOT NULL,
                    target TEXT,
                    payload TEXT,
                    metadata TEXT,
                    tag TEXT,
                    time_spec TEXT NOT NULL,               -- point | interval | condition
                    at REAL,                                -- for point
                    interval_start REAL,                    -- for interval
                    interval_end REAL,                      -- for interval
                    law TEXT,                               -- for interval
                    condition_expr TEXT,                    -- JSON AST for conditions
                    dependency_id TEXT,                     -- event id this depends on
                    priority INTEGER DEFAULT 0,
                    status TEXT NOT NULL,                   -- pending|scheduled|active|completed|canceled|failed|locked
                    due_at REAL,                            -- point due time, or interval_start
                    created_at REAL NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT,
                    idempotency_key TEXT UNIQUE,
                    locked_by TEXT,
                    locked_at REAL
                )
                """
            )
            # Try to add simulation namespace column if missing (best-effort migration)
            try:
                cur.execute("ALTER TABLE events ADD COLUMN simulation TEXT")
            except sqlite3.OperationalError:
                # Column likely already exists
                pass
            try:
                cur.execute("ALTER TABLE events ADD COLUMN metadata TEXT")
            except sqlite3.OperationalError:
                # Column likely already exists
                pass
            try:
                cur.execute("ALTER TABLE events ADD COLUMN tag TEXT")
            except sqlite3.OperationalError:
                # Column likely already exists
                pass
            self._backfill_legacy_tags(cur)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_status_due ON events(status, due_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_dependency ON events(dependency_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_time ON events(at, interval_start, interval_end)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_sim_status_due ON events(simulation, status, due_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_sim_tag_created ON events(simulation, tag, created_at)"
            )
            conn.commit()

    @staticmethod
    def _extract_legacy_tag(metadata_raw: Any) -> Optional[str]:
        """Best-effort extraction of a tag from legacy event metadata."""
        if not metadata_raw:
            return None
        try:
            metadata = orjson.loads(metadata_raw)
        except Exception:
            return None
        if not isinstance(metadata, dict):
            return None

        tag = metadata.get("tag")
        if isinstance(tag, str):
            tag = tag.strip()
            if tag:
                return tag

        dsl_text = metadata.get("dsl_text")
        if not isinstance(dsl_text, str):
            return None

        match = _TAGGED_DSL_RE.search(dsl_text)
        if not match:
            return None
        tag = match.group(1).strip()
        return tag or None

    def _backfill_legacy_tags(self, cur: sqlite3.Cursor) -> None:
        """Populate the tag column for legacy rows that only stored metadata."""
        try:
            rows = cur.execute(
                """
                SELECT id, metadata
                FROM events
                WHERE tag IS NULL
                  AND source IN ('dsl', 'trainer')
                  AND metadata IS NOT NULL
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return

        updates: List[Tuple[str, str]] = []
        for row in rows:
            tag = self._extract_legacy_tag(row["metadata"])
            event_id = row["id"]
            if not tag or not event_id:
                continue
            updates.append((tag, str(event_id)))

        if updates:
            cur.executemany(
                "UPDATE events SET tag = ? WHERE id = ? AND tag IS NULL",
                updates,
            )

    @staticmethod
    def _now() -> float:
        """
        Return the current UNIX timestamp.

        Returns:
            float: Current system time in seconds.
        """
        return time.time()

    def enqueue_event(
        self,
        *,
        source: str,
        type: str,
        target: Optional[Any],
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        time_spec: str,
        at: Optional[float] = None,
        interval_start: Optional[float] = None,
        interval_end: Optional[float] = None,
        law: Optional[str] = None,
        condition_expr: Optional[Dict[str, Any]] = None,
        dependency_id: Optional[str] = None,
        priority: int = 0,
        idempotency_key: Optional[str] = None,
        status: Optional[str] = None,
        event_id: Optional[str] = None,
        simulation: Optional[str] = None,
        due_at: Optional[float] = None,
        tag: Optional[str] = None,
    ) -> str:
        """
        Insert an event, respecting idempotency if provided.
        Returns the event id.
        """
        if time_spec not in ("point", "interval", "condition"):
            raise ValueError("time_spec must be one of: point, interval, condition")

        if status is None:
            # Default status based on type
            if time_spec == "point":
                status = "scheduled"
            elif time_spec == "interval":
                status = "scheduled"
            else:
                status = "pending"

        computed_due_at = None
        if due_at is None:
            if time_spec == "point":
                computed_due_at = at
            elif time_spec == "interval":
                computed_due_at = interval_start
        else:
            computed_due_at = due_at

        eid = event_id or str(uuid.uuid4())
        created_at = self._now()
        target_json = orjson.dumps(target).decode() if target is not None else None
        payload_json = orjson.dumps(payload).decode() if payload is not None else None
        metadata_json = (
            orjson.dumps(metadata).decode() if metadata is not None else None
        )
        cond_json = (
            orjson.dumps(condition_expr).decode()
            if condition_expr is not None
            else None
        )

        with self._connect() as conn:
            cur = conn.cursor()
            if idempotency_key is not None:
                # Try to insert; if conflict, fetch existing id
                try:
                    cur.execute(
                        """
                        INSERT INTO events (
                            id, source, type, target, payload, metadata, tag, time_spec,
                            at, interval_start, interval_end, law, condition_expr,
                            dependency_id, priority, status, due_at, created_at,
                            idempotency_key, simulation
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            eid,
                            source,
                            type,
                            target_json,
                            payload_json,
                            metadata_json,
                            tag,
                            time_spec,
                            at,
                            interval_start,
                            interval_end,
                            law,
                            cond_json,
                            dependency_id,
                            priority,
                            status,
                            computed_due_at,
                            created_at,
                            idempotency_key,
                            simulation,
                        ),
                    )
                except sqlite3.IntegrityError:
                    row = cur.execute(
                        "SELECT id FROM events WHERE idempotency_key = ?",
                        (idempotency_key,),
                    ).fetchone()
                    return row[0] if row else eid
            else:
                cur.execute(
                    """
                    INSERT INTO events (
                        id, source, type, target, payload, metadata, tag, time_spec,
                        at, interval_start, interval_end, law, condition_expr,
                        dependency_id, priority, status, due_at, created_at,
                        simulation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        eid,
                        source,
                        type,
                        target_json,
                        payload_json,
                        metadata_json,
                        tag,
                        time_spec,
                        at,
                        interval_start,
                        interval_end,
                        law,
                        cond_json,
                        dependency_id,
                        priority,
                        status,
                        computed_due_at,
                        created_at,
                        simulation,
                    ),
                )
            conn.commit()
        return eid

    def events_due(
        self, t: float, eps: float, simulation: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Return due point events and active intervals for time t.
        """
        sim_clause = " AND simulation = ?" if simulation else ""
        sim_params: Tuple[Any, ...] = (simulation,) if simulation else tuple()
        with self._connect() as conn:
            cur = conn.cursor()
            pt_rows = cur.execute(
                """
                SELECT * FROM events
                WHERE time_spec = 'point' AND status = 'scheduled'
                  AND due_at >= ? AND due_at <= ?
                """
                + sim_clause
                + """
                ORDER BY due_at, priority DESC, created_at
                """,
                (t - eps, t + eps) + sim_params,
            ).fetchall()
            int_rows = cur.execute(
                """
                SELECT * FROM events
                WHERE time_spec = 'interval' AND status IN ('scheduled','active')
                  AND (
                    (due_at IS NOT NULL AND due_at <= ?)
                    OR (due_at IS NULL AND interval_start <= ?)
                  )
                  AND interval_end >= ?
                """
                + sim_clause
                + """
                ORDER BY interval_start, priority DESC, created_at
                """,
                (t, t, t) + sim_params,
            ).fetchall()

        def row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
            """
            Convert a SQLite row into a dictionary with decoded JSON columns.

            Args:
                r (sqlite3.Row): Row returned from the events table.

            Returns:
                Dict[str, Any]: Dictionary representation with JSON fields parsed.
            """
            d = dict(r)
            for k in ("target", "payload", "metadata", "condition_expr"):
                if d.get(k):
                    try:
                        d[k] = orjson.loads(d[k])
                    except Exception:
                        pass
            return d

        return {
            "points": [row_to_dict(r) for r in pt_rows],
            "intervals": [row_to_dict(r) for r in int_rows],
        }

    def update_payload(self, event_id: str, payload: Optional[Dict[str, Any]]) -> bool:
        """
        Replace the payload for an existing event.

        Args:
            event_id (str): Identifier of the event to mutate.
            payload (Optional[Dict[str, Any]]): New payload data; ``None``
                clears the existing payload.

        Returns:
            bool: ``True`` when an event was updated.
        """
        if not event_id:
            return False
        payload_json = orjson.dumps(payload).decode() if payload is not None else None
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE events SET payload = ? WHERE id = ?",
                (payload_json, event_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def update_payloads_batch(self, updates: List[Tuple[str, Optional[Dict[str, Any]]]]) -> int:
        """
        Update payloads for multiple events in a single transaction.

        This is a performance-optimized batch version of update_payload() that
        reduces database round-trips when updating many events at once.

        Args:
            updates (List[Tuple[str, Optional[Dict[str, Any]]]]): List of
                (event_id, payload) tuples to update.

        Returns:
            int: Number of events updated.
        """
        if not updates:
            return 0

        params = []
        for event_id, payload in updates:
            if not event_id:
                continue
            payload_json = orjson.dumps(payload).decode() if payload is not None else None
            params.append((payload_json, event_id))

        if not params:
            return 0

        with self._connect() as conn:
            cur = conn.cursor()
            cur.executemany(
                "UPDATE events SET payload = ? WHERE id = ?",
                params
            )
            conn.commit()
            return cur.rowcount or 0

    @staticmethod
    def _decoded_payload(row: sqlite3.Row) -> Dict[str, Any]:
        payload = row["payload"]
        if not payload:
            return {}
        try:
            decoded = orjson.loads(payload)
        except Exception:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    @staticmethod
    def _all_children_completed(
        cur: sqlite3.Cursor,
        child_event_ids: List[str],
    ) -> bool:
        if not child_event_ids:
            return True
        placeholders = ",".join("?" for _ in child_event_ids)
        rows = cur.execute(
            f"SELECT id FROM events WHERE status = 'completed' AND id IN ({placeholders})",
            tuple(child_event_ids),
        ).fetchall()
        completed_ids = {str(row["id"]) for row in rows}
        return all(str(event_id) in completed_ids for event_id in child_event_ids)

    def _resolve_function_completion_markers(
        self,
        cur: sqlite3.Cursor,
    ) -> List[str]:
        newly_completed: List[str] = []
        while True:
            rows = cur.execute(
                """
                SELECT id, payload
                FROM events
                WHERE type = 'function_completion'
                  AND status != 'completed'
                """
            ).fetchall()
            eligible: List[str] = []
            for row in rows:
                payload = self._decoded_payload(row)
                if not payload.get("expanded"):
                    continue
                child_event_ids = [
                    str(event_id)
                    for event_id in (payload.get("child_event_ids") or [])
                    if event_id
                ]
                if self._all_children_completed(cur, child_event_ids):
                    eligible.append(str(row["id"]))
            if not eligible:
                break
            cur.executemany(
                "UPDATE events SET status = 'completed' WHERE id = ?",
                [(event_id,) for event_id in eligible],
            )
            newly_completed.extend(eligible)
        return newly_completed

    def promote_ready_events(
        self, t: float, simulation: Optional[str] = None, delay: float = 0.0
    ) -> int:
        """
        Promote dependency-based point events to scheduled when their dependency
        has completed. Sets due_at to current time t.

        Returns number of events promoted.
        """
        sim_clause = " AND simulation = ?" if simulation else ""
        lead = delay if delay and delay > 0 else 0.0
        execute_at = (t if t is not None else 0.0) + lead
        due_time = max(0.0, (t if t is not None else 0.0))
        with self._connect() as conn:
            cur = conn.cursor()
            # Promote events with a completed dependency and not yet scheduled with a due time
            sql = """
                UPDATE events
                SET status = 'scheduled',
                    due_at = ?,
                    at = CASE WHEN at IS NULL OR at = 0 THEN ? ELSE at END
                WHERE time_spec = 'point'
                  AND dependency_id IS NOT NULL
                  AND (status = 'pending' OR (status = 'scheduled' AND (due_at IS NULL OR due_at = 0)))
                  AND dependency_id IN (
                      SELECT id FROM events WHERE status = 'completed'
                )
                """ + (
                " AND simulation = ?" if simulation else ""
            )
            params: List[Any] = [due_time, execute_at]
            if simulation:
                params.append(simulation)
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount or 0

    def reschedule_point_events(
        self, event_ids: Iterable[str], new_due_at: float, lead_time: float = 0.0
    ) -> None:
        """Move point events to a new due time so they can be retried later."""

        ids = [eid for eid in event_ids if eid]
        if not ids:
            return
        lead = lead_time if lead_time and lead_time > 0 else 0.0
        due_at = max(0.0, new_due_at - lead)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.executemany(
                "UPDATE events SET status = 'scheduled', due_at = ?, at = ? WHERE id = ? AND time_spec = 'point' AND status != 'completed'",
                [(due_at, new_due_at, eid) for eid in ids],
            )
            conn.commit()

    def mark_completed(
        self, event_ids: Iterable[str], completed_at: Optional[float] = None
    ) -> None:
        """
        Mark one or more events as completed.

        Args:
            event_ids (Iterable[str]): Collection of event identifiers.
            completed_at (Optional[float]): Timestamp associated with the
                completion; defaults to ``_now()``.
        """
        if not event_ids:
            return
        ts = completed_at if completed_at is not None else self._now()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.executemany(
                "UPDATE events SET status = 'completed' WHERE id = ?",
                [(eid,) for eid in event_ids],
            )
            self._resolve_function_completion_markers(cur)
            conn.commit()

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Return a single event by id with JSON fields decoded when possible."""
        if not event_id:
            return None
        with self._connect() as conn:
            cur = conn.cursor()
            row = cur.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()
        if row is None:
            return None
        event = dict(row)
        for key in ("target", "payload", "metadata", "condition_expr"):
            value = event.get(key)
            if value:
                try:
                    event[key] = orjson.loads(value)
                except Exception:
                    pass
        return event

    def delete_event(self, event_id: str) -> int:
        """Remove a single event by id. Returns number of rows deleted."""
        if not event_id:
            return 0
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            return cur.rowcount or 0

    def replace_event(
        self,
        old_event_id: str,
        *,
        source: str,
        type: str,
        target: Optional[Any],
        payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        time_spec: str,
        at: Optional[float] = None,
        interval_start: Optional[float] = None,
        interval_end: Optional[float] = None,
        law: Optional[str] = None,
        condition_expr: Optional[Dict[str, Any]] = None,
        dependency_id: Optional[str] = None,
        priority: int = 0,
        status: Optional[str] = None,
        simulation: Optional[str] = None,
        due_at: Optional[float] = None,
        tag: Optional[str] = None,
    ) -> str:
        """
        Atomically delete an old event and insert a new one, preserving the original ID.

        This is used for modifying events: the old event is removed and the new one
        takes its place with the same event_id for tracking continuity.

        Args:
            old_event_id: The ID of the event to replace (will be reused for new event).
            Other args: Same as enqueue_event.

        Returns:
            str: The event_id (same as old_event_id).

        Raises:
            ValueError: If old_event_id is not found (race condition protection).
        """
        if time_spec not in ("point", "interval", "condition"):
            raise ValueError("time_spec must be one of: point, interval, condition")

        if status is None:
            if time_spec == "point":
                status = "scheduled"
            elif time_spec == "interval":
                status = "scheduled"
            else:
                status = "pending"

        computed_due_at = None
        if due_at is None:
            if time_spec == "point":
                computed_due_at = at
            elif time_spec == "interval":
                computed_due_at = interval_start
        else:
            computed_due_at = due_at

        created_at = self._now()
        target_json = orjson.dumps(target).decode() if target is not None else None
        payload_json = orjson.dumps(payload).decode() if payload is not None else None
        metadata_json = (
            orjson.dumps(metadata).decode() if metadata is not None else None
        )
        cond_json = (
            orjson.dumps(condition_expr).decode()
            if condition_expr is not None
            else None
        )

        with self._connect() as conn:
            cur = conn.cursor()
            # Delete old event first
            cur.execute("DELETE FROM events WHERE id = ?", (old_event_id,))
            if (cur.rowcount or 0) == 0:
                raise ValueError(f"Event {old_event_id} not found or already deleted")

            # Insert new event with the SAME id for tracking continuity
            cur.execute(
                """
                INSERT INTO events (
                    id, source, type, target, payload, metadata, tag, time_spec,
                    at, interval_start, interval_end, law, condition_expr,
                    dependency_id, priority, status, due_at, created_at,
                    simulation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    old_event_id,
                    source,
                    type,
                    target_json,
                    payload_json,
                    metadata_json,
                    tag,
                    time_spec,
                    at,
                    interval_start,
                    interval_end,
                    law,
                    cond_json,
                    dependency_id,
                    priority,
                    status,
                    computed_due_at,
                    created_at,
                    simulation,
                ),
            )
            conn.commit()
        return old_event_id

    def get_latest_tag_bindings(
        self,
        simulation: str,
        *,
        exclude_event_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Return the latest surviving event binding for each tag in a simulation."""
        if not simulation:
            return {}

        clauses = [
            "simulation = ?",
            "tag IS NOT NULL",
            "(source IN ('dsl', 'trainer') OR type = 'function_completion')",
            "status IN ('pending', 'scheduled', 'active', 'locked', 'completed')",
        ]
        params: List[Any] = [simulation]
        if exclude_event_id:
            clauses.append("id != ?")
            params.append(exclude_event_id)

        sql = (
            "SELECT id, tag FROM events WHERE "
            + " AND ".join(clauses)
            + " ORDER BY created_at DESC, id DESC"
        )

        bindings: Dict[str, str] = {}
        with self._connect() as conn:
            cur = conn.cursor()
            rows = cur.execute(sql, params).fetchall()

        for row in rows:
            tag = row["tag"]
            event_id = row["id"]
            if not tag or not event_id or tag in bindings:
                continue
            bindings[str(tag)] = str(event_id)
        return bindings

    def list_events(
        self,
        *,
        status: Optional[str] = None,
        source: Optional[str] = None,
        time_spec: Optional[str] = None,
        simulation: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve events that match optional filters sorted by recency.

        Args:
            status (Optional[str]): Filter by event status such as
                ``scheduled`` or ``completed``.
            source (Optional[str]): Restrict results to a particular
                source (trainer, user, etc.).
            time_spec (Optional[str]): Filter by time specification.
            simulation (Optional[str]): Scope the query to one simulation.
            limit (int): Maximum number of events to fetch.
            offset (int): Number of rows to skip for pagination.

        Returns:
            List[Dict[str, Any]]: Event dictionaries with decoded JSON
            payloads and targets.

        Examples:
            >>> store.list_events(status=\"scheduled\", limit=5)
            [{'id': '...', 'status': 'scheduled'}, ...]
        """
        clauses = []
        params: List[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if time_spec:
            clauses.append("time_spec = ?")
            params.append(time_spec)
        if simulation:
            clauses.append("simulation = ?")
            params.append(simulation)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            "SELECT * FROM events"
            + where
            + " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([int(limit), int(offset)])
        with self._connect() as conn:
            cur = conn.cursor()
            rows = cur.execute(sql, params).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            for k in ("target", "payload", "metadata", "condition_expr"):
                if d.get(k):
                    try:
                        d[k] = orjson.loads(d[k])
                    except Exception:
                        pass
            out.append(d)
        return out

    def purge_simulation(self, simulation: str) -> int:
        """Delete all events for a given simulation. Returns number of rows removed."""
        if not simulation:
            return 0
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM events WHERE simulation = ?", (simulation,))
            conn.commit()
            return cur.rowcount or 0

    def purge_all(self) -> int:
        """Delete every event from the store. Returns number of rows removed."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM events")
            deleted = cur.rowcount or 0
            conn.commit()
            return deleted

    def trainer_event_summary(
        self,
        simulation: Optional[str] = None,
        current_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return aggregate information about pending trainer events."""

        clauses = ["source = 'trainer'", "(status IS NULL OR status != 'completed')"]
        params: List[Any] = []
        if simulation:
            clauses.append("simulation = ?")
            params.append(simulation)
        where = " WHERE " + " AND ".join(clauses)

        summary = {
            "future_count": 0,
            "skipped_count": 0,
            "completed_count": 0,
            "total_count": 0,
            "count": 0,
            "type_breakdown": {},
            "earliest": None,
            "latest": None,
        }

        with self._connect() as conn:
            cur = conn.cursor()
            pending_row = cur.execute(
                f"SELECT COUNT(*) AS c FROM events{where}",
                params,
            ).fetchone()
            pending_count = int(pending_row["c"]) if pending_row else 0
            summary["count"] = pending_count

            completed_row = cur.execute(
                """
                SELECT COUNT(*) AS c FROM events
                WHERE source = 'trainer'
                  AND status = 'completed'
                """
                + (" AND simulation = ?" if simulation else ""),
                ([simulation] if simulation else []),
            ).fetchone()
            completed_count = int(completed_row["c"]) if completed_row else 0

            summary["completed_count"] = completed_count
            summary["total_count"] = completed_count + pending_count

            breakdown_rows = cur.execute(
                f"SELECT type, COUNT(*) AS cnt FROM events{where} GROUP BY type",
                params,
            ).fetchall()
            summary["type_breakdown"] = {
                (row["type"] or "unknown"): int(row["cnt"]) for row in breakdown_rows
            }

            earliest_row = cur.execute(
                f"SELECT MIN(CASE WHEN time_spec = 'interval' THEN interval_start ELSE at END) AS min_time FROM events{where}",
                params,
            ).fetchone()
            latest_row = cur.execute(
                f"SELECT MAX(CASE WHEN time_spec = 'interval' THEN interval_end ELSE at END) AS max_time FROM events{where}",
                params,
            ).fetchone()
            summary["earliest"] = earliest_row["min_time"] if earliest_row else None
            summary["latest"] = latest_row["max_time"] if latest_row else None

            event_rows = cur.execute(
                f"""
                SELECT time_spec, at, interval_start, interval_end, due_at, dependency_id
                FROM events
                {where}
                """,
                params,
            ).fetchall()

            if current_time is not None and event_rows:
                future_starts: List[float] = []
                future_ends: List[float] = []
                unresolved_dependency_count = 0
                for row in event_rows:
                    if row["time_spec"] == "interval":
                        start = row["interval_start"]
                        end = row["interval_end"] or start
                    else:
                        start = row["at"] or row["due_at"]
                        end = start
                    if start is None:
                        if row["dependency_id"] is not None:
                            unresolved_dependency_count += 1
                            continue
                        start = row["due_at"]
                        end = end or start
                    if start is not None and start >= current_time:
                        future_starts.append(start)
                        future_ends.append(end if end is not None else start)
                future_count = len(future_starts) + unresolved_dependency_count
                summary["future_count"] = future_count
                summary["skipped_count"] = pending_count - future_count
                if future_starts:
                    summary["earliest"] = min(future_starts)
                    summary["latest"] = max(future_ends)
                else:
                    summary["earliest"] = None
                    summary["latest"] = None
            else:
                summary["future_count"] = pending_count

        return summary

    def mark_failed(self, event_ids: Iterable[str], error: str | None = None) -> None:
        """Mark events as failed and store last_error for diagnostics."""
        ids = [eid for eid in event_ids if eid]
        if not ids:
            return
        with self._connect() as conn:
            cur = conn.cursor()
            cur.executemany(
                "UPDATE events SET status = 'failed', last_error = ? WHERE id = ?",
                [(error or "", eid) for eid in ids],
            )
            conn.commit()
