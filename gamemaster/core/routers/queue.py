"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Expose diagnostic endpoints for inspecting the event-store backlog.

These routes provide lightweight listings and summaries useful for
operators that need visibility into DSL/user events without accessing
the database directly.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import orjson
from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from fastapi import APIRouter, Body, HTTPException, Query, Request

from ..domain.controllers.global_instances import get_event_store, get_simulation_controller
from ..services.dsl_logging import get_dsl_logger
from ..services.tag_context import seed_labels
from ..utils.clock import get_current_time
from ..utils.DSLEngine import DSLInterpreter
from ..utils.DSLEngine.antlr.PowerEventDSLLexer import PowerEventDSLLexer
from ..utils.DSLEngine.antlr.PowerEventDSLParser import PowerEventDSLParser

router = APIRouter(tags=["Event Store"])
logger = logging.getLogger(__name__)
_DELETABLE_STATUSES = {"pending", "scheduled", "active", "locked"}
_DELETABLE_SOURCES = {"dsl", "trainer"}

class _CollectingErrorListener(ErrorListener):
    """Capture lexer/parser syntax errors for API responses."""

    def __init__(self) -> None:
        super().__init__()
        self.errors: List[Dict[str, Any]] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        entry = {"line": line, "column": column, "message": msg}
        token_text = getattr(offendingSymbol, "text", None)
        if token_text:
            entry["token"] = token_text
        self.errors.append(entry)


def _format_dsl_errors(errors: List[Dict[str, Any]]) -> str:
    """Format DSL parse errors into a single line."""
    parts = []
    for entry in errors:
        line = entry.get("line")
        column = entry.get("column")
        msg = entry.get("message") or "syntax error"
        token = entry.get("token")
        loc = f"line {line}:{column}" if line is not None else "line ?"
        if token:
            parts.append(f"{loc} {msg} at '{token}'")
        else:
            parts.append(f"{loc} {msg}")
    return "; ".join(parts)


class _CollectingEventStore:
    """Minimal event-store façade used to record DSL events prior to persistence."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

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
        import uuid

        eid = event_id or str(uuid.uuid4())
        entry = {
            "event_id": eid,
            "source": source,
            "type": type,
            "target": target,
            "payload": payload,
            "metadata": metadata,
            "time_spec": time_spec,
            "at": at,
            "interval_start": interval_start,
            "interval_end": interval_end,
            "law": law,
            "condition_expr": condition_expr,
            "dependency_id": dependency_id,
            "priority": priority,
            "idempotency_key": idempotency_key,
            "status": status,
            "simulation": simulation,
            "due_at": due_at,
            "tag": tag,
        }
        self.events.append(entry)
        return eid


@router.get("/list")
def list_events(
    status: Optional[str] = Query(
        None,
        description="Filter by status: pending|scheduled|active|completed|canceled|failed|locked",
    ),
    source: Optional[str] = Query(
        None, description="Filter by source: dsl|user|system"
    ),
    time_spec: Optional[str] = Query(
        None, description="Filter by timing: point|interval|condition"
    ),
    simulation: Optional[str] = Query(None, description="Filter by simulation name"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Return a paginated listing of event-store entries.

    Args:
        status (Optional[str]): Optional status filter.
        source (Optional[str]): Filter by event source.
        time_spec (Optional[str]): Filter by time spec.
        simulation (Optional[str]): Filter by simulation name.
        limit (int): Maximum number of events to fetch.
        offset (int): Number of rows to skip for pagination.

    Returns:
        dict: Items and total count for the requested slice.
    """
    try:
        store = get_event_store()
        items = store.list_events(
            status=status,
            source=source,
            time_spec=time_spec,
            simulation=simulation,
            limit=limit,
            offset=offset,
        )
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _log_event_deletion(event: dict) -> None:
    """Record a deletion entry in the DSL execution log."""
    logger = get_dsl_logger()
    if logger is None:
        return
    simulation = event.get("simulation")
    source = (event.get("source") or "gamemaster").lower()
    metadata = {
        "event_id": event.get("id"),
        "type": event.get("type"),
        "target": event.get("target"),
        "status": event.get("status"),
        "time_spec": event.get("time_spec"),
        "due_at": event.get("due_at"),
        "at": event.get("at"),
    }
    event_metadata = event.get("metadata")
    if isinstance(event_metadata, dict):
        metadata["metadata"] = event_metadata
    try:
        dsl_text = None
        if isinstance(event_metadata, dict):
            dsl_text = event_metadata.get("dsl_text")
        if not dsl_text:
            target = event.get("target")
            target_repr = (
                json.dumps(target, ensure_ascii=True)
                if target is not None
                else "None"
            )
            dsl_text = (
                f"// deleted event {event.get('id')}: "
                f"{event.get('type')} -> {target_repr}"
            )
        sim_time = get_current_time(simulation) if simulation else None
        await logger.record_entry(
            simulation=simulation,
            entry_type="deletion",
            source=source,
            dsl_text=dsl_text,
            sim_time=sim_time,
            metadata=metadata,
            event_id=event.get("id"),
            status="deleted",
        )
    except Exception:
        # Logging failures should not block deletion
        return


async def _log_event_modification(
    original_event: dict,
    new_event: dict,
    original_dsl: str,
    new_dsl: str,
) -> None:
    """Record a modification entry in the DSL execution log."""
    dsl_logger = get_dsl_logger()
    if dsl_logger is None:
        return

    simulation = new_event.get("simulation")
    source = (new_event.get("source") or "trainer").lower()

    # Build audit trail comment with clear before/after
    original_lines = original_dsl.replace("\n", "\n// ")
    dsl_text = (
        f"// --- MODIFIED event {new_event.get('id')} ---\n"
        f"// Original:\n"
        f"// {original_lines}\n"
        f"// Replacement:\n"
        f"{new_dsl}"
    )

    metadata = {
        "event_id": new_event.get("id"),
        "type": new_event.get("type"),
        "before": {
            "at": original_event.get("at"),
            "interval_start": original_event.get("interval_start"),
            "interval_end": original_event.get("interval_end"),
            "target": original_event.get("target"),
            "payload": original_event.get("payload"),
            "time_spec": original_event.get("time_spec"),
        },
        "after": {
            "at": new_event.get("at"),
            "interval_start": new_event.get("interval_start"),
            "interval_end": new_event.get("interval_end"),
            "target": new_event.get("target"),
            "payload": new_event.get("payload"),
            "time_spec": new_event.get("time_spec"),
        },
        "original_dsl": original_dsl,
        "new_dsl": new_dsl,
    }

    try:
        sim_time = get_current_time(simulation) if simulation else None
        await dsl_logger.record_entry(
            simulation=simulation,
            entry_type="modification",
            source=source,
            dsl_text=dsl_text,
            sim_time=sim_time,
            metadata=metadata,
            event_id=new_event.get("id"),
            status="modified",
        )
    except Exception:
        # Logging failures should not block modification
        pass


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    simulation: Optional[str] = Query(
        None,
        description="Optional simulation name filter; reject if id belongs to another simulation.",
    ),
):
    """
    Delete a DSL or trainer event by id when it has not completed execution.

    Only DSL or trainer events in non-terminal states are eligible.
    """
    store = get_event_store()
    event = store.get_event(event_id)
    if event is None:
        raise HTTPException(
            status_code=404, detail=f"Event '{event_id}' not found in queue."
        )

    if simulation and event.get("simulation") and event.get("simulation") != simulation:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Event '{event_id}' not found for simulation '{simulation}'. "
                "Confirm the simulation name."
            ),
        )

    source = (event.get("source") or "").lower()
    if source not in _DELETABLE_SOURCES:
        raise HTTPException(
            status_code=409,
            detail="Only DSL or trainer events can be deleted via this endpoint.",
        )

    status = (event.get("status") or "").lower()
    if status and status not in _DELETABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Event '{event_id}' is in status '{status}' and cannot be deleted. "
                "Only pending, scheduled, locked, or active DSL events are deletable."
            ),
        )

    deleted = store.delete_event(event_id)
    if deleted < 1:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete event '{event_id}'."
        )

    await _log_event_deletion(event)
    return {
        "message": "Event deleted",
        "event": event,
    }


@router.get("/summary")
def summary():
    """
    Provide aggregate counts per event status for quick monitoring.

    Returns:
        dict: Mapping of status -> count.
    """
    try:
        store = get_event_store()
        statuses = [
            "pending",
            "scheduled",
            "active",
            "completed",
            "canceled",
            "failed",
            "locked",
        ]
        out = {}
        for s in statuses:
            out[s] = len(store.list_events(status=s, limit=100000, offset=0))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{event_id}")
async def modify_event(
    event_id: str,
    request: Request,
    dsl_body: Optional[str] = Body(
        None,
        media_type="text/plain",
        description="Raw DSL command text defining the replacement event.",
    ),
    simulation: Optional[str] = Query(
        None,
        description="Optional simulation name filter; reject if id belongs to another simulation.",
    ),
):
    """
    Modify a DSL or trainer event by replacing it with a new event defined by DSL.

    The operation validates the new DSL before removing the original event,
    ensuring the queue is never left in an inconsistent state. The event ID
    is preserved for tracking continuity.

    Constraints:
    - Only events from 'dsl' or 'trainer' sources can be modified
    - Events must be in a non-terminal status (pending, scheduled, active, locked)
    - Events due within the current simulation step cannot be modified
    - The DSL must produce exactly one event
    - The new event's time_spec must match the original (point↔point, interval↔interval)
    """
    store = get_event_store()

    # --- Step 1: Parse DSL input ---
    dsl_source: Optional[str] = dsl_body if isinstance(dsl_body, str) else None

    raw_body: Optional[bytes] = None
    if dsl_source is None:
        try:
            raw_body = await request.body()
        except Exception as exc:
            logger.error("Failed to read DSL request body: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=400, detail="Unable to read DSL payload."
            ) from exc

    if dsl_source is None and raw_body:
        content_type = request.headers.get("content-type", "") or ""
        if "application/json" in content_type:
            try:
                payload = orjson.loads(raw_body)
            except orjson.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=400, detail=f"Invalid JSON payload: {exc}"
                ) from exc

            if isinstance(payload, dict):
                raw_value = payload.get("dsl")
                if isinstance(raw_value, str):
                    dsl_source = raw_value
            elif isinstance(payload, str):
                dsl_source = payload
        else:
            try:
                dsl_source = raw_body.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise HTTPException(
                    status_code=400, detail="DSL payload must be UTF-8 text."
                ) from exc

    dsl_source = (dsl_source or "").strip()
    if not dsl_source:
        raise HTTPException(status_code=400, detail="DSL payload must not be empty.")

    # --- Step 2: Fetch and validate existing event ---
    original_event = store.get_event(event_id)
    if original_event is None:
        raise HTTPException(
            status_code=404, detail=f"Event '{event_id}' not found in queue."
        )

    if simulation and original_event.get("simulation") and original_event.get("simulation") != simulation:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Event '{event_id}' not found for simulation '{simulation}'. "
                "Confirm the simulation name."
            ),
        )

    source = (original_event.get("source") or "").lower()
    if source not in _DELETABLE_SOURCES:
        raise HTTPException(
            status_code=409,
            detail="Only DSL or trainer events can be modified via this endpoint.",
        )

    status = (original_event.get("status") or "").lower()
    if status and status not in _DELETABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Event '{event_id}' is in status '{status}' and cannot be modified. "
                "Only pending, scheduled, locked, or active events are modifiable."
            ),
        )

    # --- Step 3: Check timing guard ---
    simulation_controller = get_simulation_controller()
    base_interpreter = getattr(simulation_controller, "interpreter", None)
    simulation_name = original_event.get("simulation") or getattr(
        simulation_controller, "simulation_name", None
    )

    try:
        current_time = get_current_time(simulation_name)
    except Exception:
        current_time = float(getattr(base_interpreter, "current_time", None) or 0.0)

    time_step = None
    for candidate in (
        getattr(base_interpreter, "time_step", None) if base_interpreter else None,
        1e-3,
    ):
        try:
            val = float(candidate) if candidate is not None else None
        except (TypeError, ValueError):
            val = None
        if val is not None and val > 0:
            time_step = val
            break

    if time_step is None:
        time_step = 1e-3

    due_at = original_event.get("due_at")
    if due_at is not None:
        try:
            due_at_val = float(due_at)
            if due_at_val <= current_time + time_step:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Event '{event_id}' is due within the current step "
                        f"(due_at={due_at_val}, current_time={current_time}) and cannot be modified."
                    ),
                )
        except (TypeError, ValueError):
            pass

    # --- Step 4: Parse new DSL ---
    artifact_id = getattr(base_interpreter, "artifact_id", None) if base_interpreter else None
    if not artifact_id:
        # Fall back to trying to get from simulation controller
        artifact_id = getattr(simulation_controller, "artifact_id", None)

    collector = _CollectingEventStore()
    trainer_interpreter = DSLInterpreter(
        artifact_id=artifact_id,
        event_store=collector,
        simulation_name=simulation_name,
        event_source="trainer",
    )

    # Align timing
    if base_interpreter:
        try:
            trainer_interpreter.time_step = getattr(base_interpreter, "time_step", None)
        except Exception:
            pass
        source_cache = getattr(base_interpreter, "iidm_cache", None)
        if isinstance(source_cache, dict):
            trainer_interpreter.iidm_cache = source_cache
            if hasattr(trainer_interpreter, "cluster_resolver"):
                trainer_interpreter.cluster_resolver.cache = source_cache

    try:
        trainer_interpreter.current_time = current_time
    except Exception:
        pass

    seed_labels(
        trainer_interpreter,
        store,
        simulation_name,
        base_labels=getattr(base_interpreter, "labels", None) if base_interpreter else None,
        exclude_event_id=event_id,
    )

    try:
        input_stream = InputStream(dsl_source)
        lexer = PowerEventDSLLexer(input_stream)
        lexer.removeErrorListeners()
        lexer_listener = _CollectingErrorListener()
        lexer.addErrorListener(lexer_listener)
        token_stream = CommonTokenStream(lexer)
        parser = PowerEventDSLParser(token_stream)
        parser.removeErrorListeners()
        parser_listener = _CollectingErrorListener()
        parser.addErrorListener(parser_listener)
        tree = parser.program()
        errors = lexer_listener.errors + parser_listener.errors
        if errors:
            raise ValueError(
                f"DSL contains syntax errors: {_format_dsl_errors(errors)}"
            )
        if getattr(parser, "getNumberOfSyntaxErrors", lambda: 0)() > 0:
            raise ValueError("DSL contains syntax errors.")
        trainer_interpreter.visit(tree)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to parse DSL: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid DSL script: {exc}")

    # --- Step 5: Validate new DSL ---
    if not collector.events:
        raise HTTPException(
            status_code=400,
            detail="DSL produced no events; expected exactly one.",
        )

    if len(collector.events) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"DSL produced {len(collector.events)} events; expected exactly one for modification.",
        )

    new_event_data = collector.events[0]

    # Check time_spec match
    original_time_spec = original_event.get("time_spec")
    new_time_spec = new_event_data.get("time_spec")
    if original_time_spec != new_time_spec:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change time_spec from '{original_time_spec}' to '{new_time_spec}'. "
                "Point events must remain point events, and interval events must remain intervals."
            ),
        )

    # Calculate due_at for new event
    new_due_at = new_event_data.get("due_at")
    if new_due_at is None:
        new_at = new_event_data.get("at")
        if new_at is not None:
            try:
                new_due_at = max(0.0, float(new_at) - time_step)
            except (TypeError, ValueError):
                new_due_at = None
        elif new_event_data.get("interval_start") is not None:
            new_due_at = new_event_data.get("interval_start")

    # Reject modifications that would trigger before the next simulation tick.
    new_start = None
    if new_time_spec == "point":
        new_start = new_event_data.get("at")
    elif new_time_spec == "interval":
        new_start = new_event_data.get("interval_start")
    try:
        if new_start is not None:
            start_val = float(new_start)
            cutoff = float(current_time) + float(time_step or 0)
            if start_val <= cutoff:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Cannot reschedule event '{event_id}' to start at {start_val} "
                        f"which would trigger no later than the current step "
                        f"(current_time={current_time}, lead={time_step})."
                    ),
                )
    except (TypeError, ValueError):
        pass

    # Get original DSL for logging (from metadata if available)
    original_dsl = ""
    original_metadata = original_event.get("metadata")
    if isinstance(original_metadata, dict):
        original_dsl = original_metadata.get("dsl_text") or ""
    if not original_dsl:
        # Reconstruct a representative string
        target = original_event.get("target")
        target_repr = json.dumps(target, ensure_ascii=True) if target else "None"
        original_dsl = f"// original event: {original_event.get('type')} -> {target_repr}"

    # Preserve current status when DSL does not override it
    new_status = new_event_data.get("status")
    if new_status is None:
        new_status = original_event.get("status")

    # --- Step 6: Atomic replace ---
    try:
        store.replace_event(
            event_id,
            source=new_event_data.get("source") or source,
            type=new_event_data.get("type"),
            target=new_event_data.get("target"),
            payload=new_event_data.get("payload"),
            metadata={
                **(new_event_data.get("metadata") or {}),
                "dsl_text": dsl_source,
            },
            time_spec=new_time_spec,
            at=new_event_data.get("at"),
            interval_start=new_event_data.get("interval_start"),
            interval_end=new_event_data.get("interval_end"),
            law=new_event_data.get("law"),
            condition_expr=new_event_data.get("condition_expr"),
            dependency_id=new_event_data.get("dependency_id"),
            priority=new_event_data.get("priority") or 0,
            status=new_status,
            simulation=simulation_name,
            due_at=new_due_at,
            tag=new_event_data.get("tag"),
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=409,
            detail=f"Event was modified or deleted by another process: {ve}",
        )
    except Exception as exc:
        logger.error("Failed to replace event: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to modify event: {exc}"
        )

    # --- Step 7: Log modification ---
    updated_event = store.get_event(event_id)
    await _log_event_modification(
        original_event=original_event,
        new_event=updated_event or {"id": event_id, "simulation": simulation_name},
        original_dsl=original_dsl,
        new_dsl=dsl_source,
    )

    # --- Step 8: Return response ---
    return {
        "message": "Event modified",
        "event_id": event_id,
        "previous_state": original_event,
        "current_state": updated_event,
        "simulation": simulation_name,
    }
