"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Read DSL execution logs stored in SQLite.

Endpoints provide visibility into recorded DSL snippets, reconstructed scripts,
and execution outcomes for each DSL command.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["DSL Command Logs"])


def _db_path() -> str:
    """Resolve the command log database path."""

    return os.getenv("DSL_COMMAND_LOG_DB_PATH", "data/dsl_command_logs.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    """
    Ensure the expected tables and indexes exist before querying.

    This keeps the read-only routes resilient even when the DB file
    was created before logging was enabled.
    """
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
    # Backfill missing columns in case the DB predated newer fields.
    cur.execute("PRAGMA table_info(dsl_execution_log)")
    cols = {row[1] for row in cur.fetchall()}
    for name, definition in (("event_id", "TEXT"), ("status", "TEXT")):
        if name not in cols:
            cur.execute(f"ALTER TABLE dsl_execution_log ADD COLUMN {name} {definition}")
    conn.commit()


def _normalize_row(row: sqlite3.Row) -> dict:
    created_at = row["created_at"]
    created_iso = None
    try:
        created_iso = datetime.fromtimestamp(
            float(created_at), tz=timezone.utc
        ).isoformat()
    except Exception:
        created_iso = None

    dsl_text = row["dsl_text"]
    metadata = _safe_json_load(row["metadata"])
    command_payload = None
    if isinstance(metadata, dict) and "command" in metadata:
        command_payload = metadata.get("command")
    elif row["entry_type"] == "execution":
        # Fallback to the stored DSL text blob when no explicit command payload is present.
        command_payload = _safe_json_load(dsl_text)
    if isinstance(command_payload, dict):
        command_payload = dict(command_payload)
        command_payload.pop("metadata", None)
    return {
        "simulation": row["simulation"],
        "entry_type": row["entry_type"],
        "source": row["source"],
        "sim_time": row["sim_time"],
        "created_at": created_at,
        "created_at_iso": created_iso,
        "dsl_text": dsl_text,
        "command": command_payload,
        "event_id": row["event_id"],
        "status": row["status"],
        "metadata": metadata,
    }


def _safe_json_load(blob: Any) -> Any:
    if blob is None:
        return None
    if isinstance(blob, (dict, list)):
        return blob
    try:
        return json.loads(blob)
    except Exception:
        return blob


@router.get("/simulations")
def list_simulations():
    """List simulations with entry counts and first/last timestamps."""

    try:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT simulation,
                       COUNT(*) AS count,
                       MIN(created_at) AS first_created_at,
                       MAX(created_at) AS last_created_at
                FROM dsl_execution_log
                GROUP BY simulation
                ORDER BY last_created_at DESC
                """
            ).fetchall()
        sims = []
        for r in rows:
            first_iso = None
            last_iso = None
            try:
                first_iso = datetime.fromtimestamp(
                    float(r["first_created_at"]), tz=timezone.utc
                ).isoformat()
                last_iso = datetime.fromtimestamp(
                    float(r["last_created_at"]), tz=timezone.utc
                ).isoformat()
            except Exception:
                pass
            sims.append(
                {
                    "simulation": r["simulation"],
                    "count": r["count"],
                    "first_created_at": r["first_created_at"],
                    "first_created_at_iso": first_iso,
                    "last_created_at": r["last_created_at"],
                    "last_created_at_iso": last_iso,
                }
            )
        return {"items": sims, "count": len(sims)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _fetch_simulation_entries(simulation: str) -> list[dict]:
    candidates = [simulation]
    if "_" in simulation:
        candidates.append(simulation.replace("_", " "))
    if " " in simulation:
        candidates.append(simulation.replace(" ", "_"))

    seen: set[str] = set()
    for sim_name in candidates:
        if sim_name in seen:
            continue
        seen.add(sim_name)
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT simulation, entry_type, source, sim_time, dsl_text, metadata,
                       event_id, status, created_at
                FROM dsl_execution_log
                WHERE simulation = ?
                ORDER BY created_at
                """,
                (sim_name,),
            ).fetchall()
        if rows:
            return [_normalize_row(r) for r in rows]
    return []


def _split_entries(entries: list[dict]) -> tuple[Optional[dict], list[dict]]:
    base = None
    timeline: list[dict] = []
    for entry in entries:
        if entry.get("entry_type") == "base_script" and base is None:
            base = entry
            continue
        timeline.append(entry)
    return base, timeline


def _render_timeline_entry(entry: dict) -> str:
    entry_type = entry.get("entry_type")
    ts = entry.get("created_at_iso") or ""
    source = entry.get("source") or "unknown"
    if entry_type == "append":
        header = f"// --- append from {source} at {ts} ---"
        body = entry.get("dsl_text") or ""
    elif entry_type == "execution":
        status = entry.get("status") or "executed"
        header = f"// --- execution {status} at {ts} ---"
        body_parts: list[str] = []
        dsl_text = entry.get("dsl_text")
        if dsl_text:
            body_parts.append(str(dsl_text))
        command_payload = entry.get("command")
        if command_payload is not None:
            if isinstance(command_payload, str):
                body_parts.append(command_payload)
            else:
                try:
                    body_parts.append(json.dumps(command_payload, indent=2, default=str))
                except Exception:
                    body_parts.append(str(command_payload))
        body = "\n".join(body_parts)
    elif entry_type == "deletion":
        header = f"// --- deletion from {source} at {ts} ---"
        dsl_text = entry.get("dsl_text") or ""
        body_lines: list[str] = []
        if dsl_text:
            cleaned = dsl_text.strip()
            if not cleaned.startswith("//"):
                cleaned = "// " + cleaned
            body_lines.append(cleaned)
        body = "\n".join(body_lines)
    elif entry_type == "modification":
        header = f"// --- modification from {source} at {ts} ---"
        body_lines: list[str] = []
        metadata = entry.get("metadata") or {}
        original_dsl = metadata.get("original_dsl")
        new_dsl = metadata.get("new_dsl")
        if original_dsl:
            # Comment out the original DSL
            original_commented = "// " + original_dsl.replace("\n", "\n// ")
            body_lines.append(f"// Original:")
            body_lines.append(original_commented)
        if new_dsl:
            body_lines.append(f"// Replacement:")
            body_lines.append(new_dsl)
        body = "\n".join(body_lines) if body_lines else entry.get("dsl_text") or ""
    else:
        header = f"// --- {entry_type or 'entry'} from {source} at {ts} ---"
        body = entry.get("dsl_text") or ""
    return "\n".join(filter(None, [header, body])).strip()


def _comment_block(text: str) -> str:
    """Prefix each non-empty, non-comment line with '//' while keeping indentation."""

    commented: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("//"):
            commented.append(line)
            continue
        leading_ws = line[: len(line) - len(stripped)]
        commented.append(f"{leading_ws}// {stripped}")
    return "\n".join(commented)


def _apply_deletion_to_script(script: str, entry: dict) -> tuple[str, bool]:
    """
    Replace the original DSL command with a commented deletion marker when possible.

    Returns the updated script and a flag indicating whether the replacement
    succeeded. When no match is found, the caller should append the rendered
    deletion entry instead.
    """

    if not script:
        return script, False

    dsl_text = entry.get("dsl_text")
    if not dsl_text:
        return script, False

    raw_snippet = str(dsl_text)
    snippet = raw_snippet.strip()
    if not snippet:
        return script, False

    for target in (raw_snippet, snippet):
        try:
            idx = script.index(target)
        except ValueError:
            continue

        # Avoid re-commenting if the line already starts with '//' before the match.
        line_start = script.rfind("\n", 0, idx)
        segment_start = 0 if line_start == -1 else line_start + 1
        if script[segment_start:idx].lstrip().startswith("//"):
            return script, False

        replacement = _render_timeline_entry(entry) or _comment_block(target)
        updated = script[:idx] + replacement + script[idx + len(target) :]
        return updated, True

    return script, False


def _apply_modification_to_script(script: str, entry: dict) -> tuple[str, bool]:
    """
    Replace the original DSL snippet with the new DSL and audit comment.

    Returns the updated script and a flag indicating whether the replacement
    succeeded. When no match is found, the caller should append the rendered
    modification entry instead.
    """
    if not script:
        return script, False

    metadata = entry.get("metadata") or {}
    original_dsl = metadata.get("original_dsl")
    if not original_dsl:
        return script, False

    snippet = str(original_dsl).strip()
    if not snippet:
        return script, False

    for target in (original_dsl, snippet):
        try:
            idx = script.index(target)
        except ValueError:
            continue

        # Avoid replacing if already commented
        line_start = script.rfind("\n", 0, idx)
        segment_start = 0 if line_start == -1 else line_start + 1
        if script[segment_start:idx].lstrip().startswith("//"):
            return script, False

        replacement = _render_timeline_entry(entry)
        updated = script[:idx] + replacement + script[idx + len(target) :]
        return updated, True

    return script, False


def _assemble_timeline(base_entry: Optional[dict], timeline_entries: list[dict]) -> str:
    base_script = base_entry.get("dsl_text") if base_entry else ""
    append_entries = [
        entry for entry in timeline_entries if entry.get("entry_type") == "append"
    ]
    deletion_entries = [
        entry for entry in timeline_entries if entry.get("entry_type") == "deletion"
    ]
    modification_entries = [
        entry for entry in timeline_entries if entry.get("entry_type") == "modification"
    ]
    other_entries = [
        entry
        for entry in timeline_entries
        if entry.get("entry_type") not in {"append", "deletion", "modification"}
    ]

    # First, lay down base script and all appends in order.
    script = base_script or ""
    for entry in append_entries:
        rendered = _render_timeline_entry(entry)
        if rendered:
            script = "\n\n".join(filter(None, [script, rendered]))

    # Next, apply deletions in-place when we can find the DSL snippet; otherwise append the entry.
    for entry in deletion_entries:
        script, replaced = _apply_deletion_to_script(script, entry)
        if replaced:
            continue
        rendered = _render_timeline_entry(entry)
        if rendered:
            script = "\n\n".join(filter(None, [script, rendered]))

    # Then, apply modifications in-place when we can find the DSL snippet; otherwise append the entry.
    for entry in modification_entries:
        script, replaced = _apply_modification_to_script(script, entry)
        if replaced:
            continue
        rendered = _render_timeline_entry(entry)
        if rendered:
            script = "\n\n".join(filter(None, [script, rendered]))

    # Finally, append any other timeline entries (rare for raw view).
    for entry in other_entries:
        rendered = _render_timeline_entry(entry)
        if rendered:
            script = "\n\n".join(filter(None, [script, rendered]))

    return script


@router.get("/sim/timeline/{simulation}")
def get_simulation_timeline(simulation: str):
    """Return the base DSL script and timeline entries for a simulation."""

    entries = _fetch_simulation_entries(simulation)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"No DSL execution logs found for simulation '{simulation}'.",
        )
    base_entry, timeline_entries = _split_entries(entries)
    base_script = base_entry.get("dsl_text") if base_entry else ""
    timeline_payload: list[dict] = []
    for entry in timeline_entries:
        payload_entry = {
            "entry_type": entry.get("entry_type"),
            "source": entry.get("source"),
            "sim_time": entry.get("sim_time"),
            "created_at_iso": entry.get("created_at_iso"),
            "status": entry.get("status"),
        }
        if entry.get("entry_type") == "execution":
            payload_entry["command"] = entry.get("command")
            payload_entry["dsl_text"] = entry.get("dsl_text")
        else:
            payload_entry["dsl_text"] = entry.get("dsl_text")
        timeline_payload.append(payload_entry)
    return {
        "simulation": simulation,
        "base_script": base_script,
        "timeline": timeline_payload,
    }


@router.get(
    "/sim/timeline/{simulation}/raw",
    response_class=PlainTextResponse,
    description="Return the reconstructed DSL script as plain text.",
)
def get_simulation_script_raw(simulation: str):
    entries = _fetch_simulation_entries(simulation)
    if not entries:
        raise HTTPException(
            status_code=404,
            detail=f"No DSL execution logs found for simulation '{simulation}'.",
        )
    base_entry, timeline_entries = _split_entries(entries)
    title_ts = base_entry["created_at_iso"] if base_entry else None
    title_line = (
        f"// {simulation}:{title_ts}" if title_ts else f"// {simulation}"
    )
    dsl_only_timeline = [
        entry for entry in timeline_entries if entry.get("entry_type") != "execution"
    ]
    body = _assemble_timeline(base_entry, dsl_only_timeline)
    return "\n\n".join([title_line, body]) if title_line else body


__all__ = ["router"]
