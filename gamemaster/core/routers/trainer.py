"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Trainer router implementing DSL ingestion, validation, and persistence.

The endpoints declared here allow uploading DSL scenarios, validating
IIDM context, and coordinating measurement subscriptions for new runs.
"""

import asyncio
import logging
import os
import re
import uuid
from typing import Any, Dict, Iterable, List, Optional

import orjson
from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Request,
)
from fastapi.responses import PlainTextResponse, JSONResponse
from jsonschema import validate, ValidationError

from ..domain.controllers.global_instances import (
    get_event_store,
    get_simulation_controller,
)
from ..services.dsl_subscription import ensure_measurements_subscribed
from ..services import get_nats_bridge
from ..services.dsl_logging import get_dsl_logger
from ..services.tag_context import seed_labels
from ..entities.model import SimulationConfig
from ..utils.DSLEngine import DSLInterpreter
from ..utils.DSLEngine.antlr.PowerEventDSLLexer import PowerEventDSLLexer
from ..utils.DSLEngine.antlr.PowerEventDSLParser import PowerEventDSLParser
from ..utils.clock import get_current_time, set_current_time, reset_clock
from ..utils.clickhouse_client import (
    StorageError,
    StorageNotFound,
    get_clickhouse_client,
)
from ..utils.schema_loader import load_simulation_config_schema
from ..services.value_cache import clear as clear_value_cache

router = APIRouter(tags=["Trainer"])

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)


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


def _validate_point_event_timing(
    event: Dict[str, Any],
    *,
    current_time: float,
    lead: float,
    eps: float,
) -> None:
    """Validate and normalize trainer point-event timing semantics."""

    event_id = event["event_id"]
    scheduled_at = event.get("at")
    dependency_id = event.get("dependency_id")

    if scheduled_at is None:
        if dependency_id:
            if not event.get("status"):
                event["status"] = "pending"
            return
        raise HTTPException(
            status_code=400,
            detail=f"Event {event_id} is missing a scheduled time.",
        )

    if scheduled_at <= current_time:
        logger.warning(
            "Trainer event %s scheduled at %s is behind current time %s; marking overdue.",
            event_id,
            scheduled_at,
            current_time,
        )
        event["overdue"] = True
    try:
        due_at = float(event["due_at"]) if event.get("due_at") is not None else None
    except (TypeError, ValueError):
        due_at = None
    if due_at is None:
        try:
            due_at = max(0.0, float(scheduled_at) - lead)
        except (TypeError, ValueError):
            due_at = None
    if due_at is not None:
        next_tick = current_time + lead
        min_due = next_tick - eps
        if due_at < min_due:
            event["due_at"] = next_tick
        else:
            event["due_at"] = due_at


class _CollectingEventStore:
    """Minimal event-store façade used to record DSL events prior to persistence."""

    def __init__(self) -> None:
        """Initialize the in-memory event buffer."""
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
        """
        Queue an event in memory while mirroring EventStore semantics.

        Args:
            source (str): Event source label.
            type (str): Event type.
            target (Optional[Any]): Target identifier or payload.
            payload (Optional[Dict[str, Any]]): Event payload.
            time_spec (str): Timing specification (point/interval/etc).
            at (Optional[float]): Timestamp for point events.
            interval_start (Optional[float]): Interval start time.
            interval_end (Optional[float]): Interval end time.
            law (Optional[str]): Interval law identifier.
            condition_expr (Optional[Dict[str, Any]]): Condition metadata.
            dependency_id (Optional[str]): Identifier for dependent events.
            priority (int): Priority value used for ordering.
            idempotency_key (Optional[str]): Key for deduplication.
            status (Optional[str]): Event status.
            event_id (Optional[str]): Explicit event identifier override.
            simulation (Optional[str]): Simulation namespace for the event.

        Returns:
            str: Event identifier assigned to the buffered entry.
        """
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

    def enqueue_event_from_json(
        self,
        persistent_store,
        *,
        simulation: Optional[str] = None,
        default_source: str = "trainer",
        time_step: Optional[float] = None,
        fallback_time_step: Optional[float] = None,
    ) -> int:
        """Replay stored events into a real EventStore instance."""
        persisted = 0
        lead_candidates = [time_step, fallback_time_step]
        lead = None
        for candidate in lead_candidates:
            try:
                val = float(candidate) if candidate is not None else None
            except (TypeError, ValueError):
                val = None
            if val is not None and val > 0:
                lead = val
                break
        if lead is None:
            lead = 1e-3
        for event in self.events:
            due_at = event.get("due_at")
            if due_at is None and (event.get("at") is not None):
                try:
                    due_at = max(0.0, float(event["at"]) - lead)
                except (TypeError, ValueError):
                    due_at = None
            persistent_store.enqueue_event(
                source=event.get("source") or default_source,
                type=event.get("type"),
                target=event.get("target"),
                payload=event.get("payload"),
                metadata=event.get("metadata"),
                time_spec=event.get("time_spec"),
                at=event.get("at"),
                interval_start=event.get("interval_start"),
                interval_end=event.get("interval_end"),
                law=event.get("law"),
                condition_expr=event.get("condition_expr"),
                dependency_id=event.get("dependency_id"),
                priority=event.get("priority") or 0,
                idempotency_key=event.get("idempotency_key"),
                status=event.get("status"),
                event_id=event.get("event_id"),
                simulation=simulation,
                due_at=due_at,
                tag=event.get("tag"),
            )
            persisted += 1
        return persisted


def _actions_by_id(interpreter: DSLInterpreter) -> Dict[str, Dict[str, Any]]:
    """Build a quick lookup of parsed actions keyed by event id."""
    mapping: Dict[str, Dict[str, Any]] = {}
    collections: Iterable[List[Dict[str, Any]]] = (
        getattr(interpreter, "time_events", []) or [],
        getattr(interpreter, "condition_events", []) or [],
        getattr(interpreter, "dependent_events", []) or [],
    )
    for coll in collections:
        for entry in coll or []:
            event_id = entry.get("id")
            action = entry.get("action")
            if event_id and isinstance(action, dict):
                mapping[event_id] = action
    return mapping


def _extract_component_references(action: Dict[str, Any]) -> List[tuple[str, str]]:
    """Return (component_type, component_id) pairs referenced by an action."""
    if not isinstance(action, dict):
        return []

    references: List[tuple[str, str]] = []
    event_type = str(action.get("type") or "").strip().lower()
    element_type = str(action.get("element_type") or "").strip().lower()

    def _append_many(component_type: str, values: Iterable[Any]) -> None:
        """
        Append normalized component references to the accumulator.

        Args:
            component_type (str): IIDM component category.
            values (Iterable[Any]): Raw identifiers to normalize.
        """
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                references.append((component_type, text))

    if element_type in {"load", "generator"}:
        targets = action.get("targets")
        if isinstance(targets, str):
            targets = [targets]
        _append_many(element_type, targets or [])
    elif event_type.endswith("_switch"):
        switch_id = action.get("id") or action.get("target")
        if switch_id:
            references.append(("switch", str(switch_id).strip()))
    elif event_type.endswith("_line"):
        line_id = action.get("id") or action.get("target")
        if line_id:
            references.append(("line", str(line_id).strip()))
    elif event_type in {"apply_fault", "clear_fault"}:
        comp_type = action.get("component_type")
        comp_id = action.get("id") or action.get("target")
        if comp_type and comp_id:
            references.append((str(comp_type).strip(), str(comp_id).strip()))
    else:
        single_target = action.get("target")
        if isinstance(single_target, str) and element_type:
            references.append((element_type, single_target.strip()))

    return references


def _collect_component_ids(
    resolver,
    artifact_id: str,
    component_type: str,
    cache: Dict[str, set[str]],
) -> set[str]:
    """
    Retrieve and cache component identifiers from the IIDM resolver.

    Args:
        resolver: Object exposing ``get_properties`` for IIDM artifacts.
        artifact_id (str): IIDM identifier for the simulation.
        component_type (str): Component category to inspect.
        cache (Dict[str, set[str]]): Mutable cache mapping component type
            to sets of ids.

    Returns:
        set[str]: Identifiers that exist for the requested component type.
    """
    key = (component_type or "").strip()
    if not key:
        return set()
    if key in cache:
        return cache[key]
    ids: set[str] = set()
    try:
        records = resolver.get_properties(artifact_id, component_type)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Failed to resolve %s components for %s: %s",
            component_type,
            artifact_id,
            exc,
        )
        records = []
    for record in records or []:
        identifier = record.get("id") or record.get("name")
        if identifier is None:
            continue
        ids.add(str(identifier))
    cache[key] = ids
    return ids


def _storage_client():
    """
    Return the lazily initialized storage client for trainer assets.

    Returns:
        StorageClient: Wrapper configured with DSL and IIDM buckets.
    """
    return get_clickhouse_client()


def _iidm_available(storage_client, artifact_id: str) -> bool:
    """
    Determine whether cached IIDM network data exists for `artifact_id`.

    Args:
        storage_client: Storage helper used to inspect objects.
        artifact_id (str): Artifact identifier whose cache is probed.

    Returns:
        bool: True when the ``network_data.json`` object exists.
    """
    if not artifact_id:
        return False
    bucket = storage_client.bucket_name
    cache_key = f"{artifact_id}/network_data.json"
    try:
        storage_client.stat_object(bucket, cache_key)
        return True
    except StorageNotFound:
        pass
    except StorageError as se:
        if getattr(se, "code", "") not in ("NoSuchKey", "NoSuchObject"):
            logger.error("Error checking IIDM cache for '%s': %s", artifact_id, se)
            raise
    except Exception:
        pass

    prefix = f"{artifact_id}/"
    try:
        for obj in storage_client.list_objects(
            bucket, recursive=True, prefix=prefix
        ):
            name = getattr(obj, "object_name", "") or ""
            lower = name.lower()
            if lower.endswith((".iidm", ".xiidm", ".xml", ".xz")):
                return True
    except StorageError as se:
        if getattr(se, "code", "") not in ("NoSuchKey", "NoSuchObject"):
            logger.error("Error listing IIDM objects for '%s': %s", artifact_id, se)
            raise
    except Exception as exc:
        logger.error(
            "Unexpected error while checking IIDM objects for '%s': %s",
            artifact_id,
            exc,
        )
        raise
    return False


@router.post("/dsl_command")
async def enqueue_trainer_dsl(
    request: Request,
    dsl_body: Optional[str] = Body(
        None,
        media_type="text/plain",
        description="Raw trainer DSL commands as plain text.",
    ),
):
    """Parse trainer-issued DSL commands, validate, and enqueue into the event store."""
    dsl_source: Optional[str] = dsl_body if isinstance(dsl_body, str) else None

    raw_body: Optional[bytes] = None
    if dsl_source is None:
        try:
            raw_body = await request.body()
        except Exception as exc:
            logger.error(
                "Failed to read trainer DSL request body: %s", exc, exc_info=True
            )
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

    simulation_controller = get_simulation_controller()
    base_interpreter = getattr(simulation_controller, "interpreter", None)
    if base_interpreter is None:
        raise HTTPException(status_code=400, detail="Simulation not initialized.")

    simulation_name = getattr(simulation_controller, "simulation_name", None)
    artifact_id = getattr(base_interpreter, "artifact_id", None)
    if not artifact_id:
        raise HTTPException(
            status_code=400, detail="Simulation artifact context unavailable."
        )
    event_store = get_event_store()

    collector = _CollectingEventStore()
    trainer_interpreter = DSLInterpreter(
        artifact_id=artifact_id,
        event_store=collector,
        simulation_name=simulation_name,
        event_source="trainer",
    )
    # Align trainer interpreter timing with the main simulation so due_at uses the real timestep
    try:
        trainer_interpreter.time_step = getattr(base_interpreter, "time_step", None)
    except Exception:
        pass

    # Reuse cached IIDM data when available to avoid redundant storage calls.
    source_cache = getattr(base_interpreter, "iidm_cache", None)
    if isinstance(source_cache, dict):
        trainer_interpreter.iidm_cache = source_cache
        if hasattr(trainer_interpreter, "cluster_resolver"):
            trainer_interpreter.cluster_resolver.cache = source_cache

    try:
        current_time = get_current_time(simulation_name)
    except Exception as exc:  # pragma: no cover - fallback to interpreter clock
        logger.debug(
            "Falling back to interpreter time for %s: %s", simulation_name, exc
        )
        current_time = float(getattr(base_interpreter, "current_time", None) or 0.0)
    try:
        trainer_interpreter.current_time = current_time
    except Exception:
        pass

    seed_labels(
        trainer_interpreter,
        event_store,
        simulation_name,
        base_labels=getattr(base_interpreter, "labels", None),
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
        logger.error("Failed to parse trainer DSL: %s", exc, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid DSL script: {exc}")

    if not collector.events:
        return {
            "message": "No trainer actions were parsed.",
            "simulation": simulation_name,
            "queued_events": [],
        }

    action_lookup = _actions_by_id(trainer_interpreter)
    resolver = getattr(base_interpreter, "cluster_resolver", None) or getattr(
        trainer_interpreter, "cluster_resolver", None
    )
    component_cache: Dict[str, set[str]] = {}
    lead = None
    for candidate in (
        getattr(trainer_interpreter, "time_step", None),
        getattr(base_interpreter, "time_step", None),
    ):
        try:
            value = float(candidate) if candidate is not None else None
        except (TypeError, ValueError):
            value = None
        if value is not None and value > 0:
            lead = value
            break
    if lead is None:
        lead = 1e-3
    eps = max(1e-3, lead / 10.0)
    try:
        current_time = float(current_time)
    except (TypeError, ValueError):
        current_time = 0.0

    for event in collector.events:
        event_id = event["event_id"]
        time_spec = str(event.get("time_spec") or "").strip().lower()

        if time_spec == "point":
            _validate_point_event_timing(
                event,
                current_time=current_time,
                lead=lead,
                eps=eps,
            )
        elif time_spec == "interval":
            interval_start = event.get("interval_start")
            interval_end = event.get("interval_end")
            if interval_start is None or interval_end is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Interval event {event_id} is missing start or end time.",
                )
            if interval_end <= interval_start:
                raise HTTPException(
                    status_code=400,
                    detail=f"Interval event {event_id} must have end time greater than start time.",
                )
            if interval_start <= current_time:
                logger.warning(
                    "Interval trainer event %s starts at %s while current time is %s; marking overdue.",
                    event_id,
                    interval_start,
                    current_time,
                )
                event["overdue"] = True
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Event {event_id} uses unsupported timing '{time_spec}'. Only point and interval events are allowed.",
            )

        action = action_lookup.get(event_id)
        element_type = str(action.get("element_type") if action else "").strip().lower()
        if element_type in {"load", "generator"}:
            targets = action.get("targets") if isinstance(action, dict) else None
            if isinstance(targets, str):
                targets = [targets]
            if not targets:
                raise HTTPException(
                    status_code=404,
                    detail=f"Event {event_id} does not resolve any {element_type} targets.",
                )
        references = _extract_component_references(action)
        if references and resolver is None:
            raise HTTPException(
                status_code=500,
                detail="Component resolver unavailable for validation.",
            )
        for component_type, component_id in references:
            known_ids = _collect_component_ids(
                resolver, artifact_id, component_type, component_cache
            )
            if component_id not in known_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unknown {component_type} id '{component_id}' referenced by event {event_id}.",
                )

    enqueue_count = collector.enqueue_event_from_json(
        event_store,
        simulation=simulation_name,
        time_step=getattr(trainer_interpreter, "time_step", None),
        fallback_time_step=getattr(base_interpreter, "time_step", None),
    )
    queue_summary = event_store.trainer_event_summary(
        simulation=simulation_name,
        current_time=current_time,
    )

    new_keys = getattr(trainer_interpreter, "new_measurement_keys", set())
    if new_keys:
        # Fire-and-forget subscription requests so enqueue is not blocked by NATS responsiveness.
        async def _subscribe_background():
            try:
                await ensure_measurements_subscribed(
                    new_keys,
                    simulation_name=simulation_name,
                    metadata={"source": "trainer", "queued": enqueue_count},
                )
            except Exception:
                logger.debug("Background trainer subscription failed", exc_info=True)

        asyncio.create_task(_subscribe_background())

    dsl_logger = get_dsl_logger()
    if dsl_logger:
        try:
            await dsl_logger.record_append(
                simulation=simulation_name,
                source="trainer",
                dsl_text=dsl_source,
                sim_time=current_time,
                metadata={"queued_events": enqueue_count},
            )
        except Exception:
            logger.debug("Failed to log DSL append", exc_info=True)

    return {
        "message": "Trainer actions queued",
        "simulation": simulation_name,
        "current_time": current_time,
        "pending_event_count": queue_summary.get("future_count", 0),
        "skipped_event_count": queue_summary.get("skipped_count", 0),
        "completed_event_count": queue_summary.get("completed_count", 0),
        "trainer_total_event_count": queue_summary.get("total_count", enqueue_count),
        "type_breakdown": queue_summary.get("type_breakdown", {}),
        "earliest_scheduled_time": queue_summary.get("earliest"),
        "latest_scheduled_time": queue_summary.get("latest"),
    }


@router.post("/init", response_model=SimulationConfig)
async def init_scenario(
    dsl_file: Optional[UploadFile] = File(None),
    simulationName: str = Form("Default Simulation"),
    artifact_id: str = Form("ieee14bus"),
):
    """
    Initialize a trainer scenario by loading DSL and IIDM context from storage.

    Args:
        dsl_file (Optional[UploadFile]): Uploaded DSL file when a stored
            version is not available.
        simulationName (str): Simulation identifier used for persistence.
        artifact_id (str): IIDM artifact identifier for validation.

    Returns:
        SimulationConfig: Parsed configuration for the initialized scenario.
    """
    try:
        # Determine canonical key for this simulation's DSL
        normalized_name = simulationName.replace(" ", "_")
        exact_key = f"{normalized_name}.dsl"
        storage = _storage_client()
        dsl_bucket = storage.dsl_bucket

        # Try to find an existing DSL by this simulation name (canonical first)
        existing_key: Optional[str] = None
        try:
            storage.stat_object(dsl_bucket, exact_key)
            existing_key = exact_key
            logger.debug(f"Found existing DSL for '{simulationName}' at '{exact_key}'.")
        except StorageError as se:
            if getattr(se, "code", "") not in ("NoSuchKey", "NoSuchObject"):
                logger.error(f"Error checking existing DSL in storage: {str(se)}")
                raise

        # If no canonical file, look for a single legacy match '<name>_<uuid>.dsl'
        if existing_key is None:
            prefix = f"{normalized_name}_"
            legacy = []
            try:
                for obj in storage.list_objects(
                    dsl_bucket, recursive=True, prefix=prefix
                ):
                    name = getattr(obj, "object_name", None)
                    if name and name.endswith(".dsl"):
                        legacy.append(name)
            except Exception:
                pass
            if len(legacy) == 1:
                existing_key = legacy[0]
                logger.debug(
                    f"Using legacy DSL for '{simulationName}' at '{existing_key}'."
                )
            elif len(legacy) > 1:
                raise HTTPException(
                    status_code=409,
                    detail=f"Multiple DSLs found for '{simulationName}'. Please clean duplicates.",
                )

        # Resolve DSL source: existing object or uploaded file
        if existing_key:
            # Load from storage
            dsl_bytes = storage.get_file(existing_key, bucket_name=dsl_bucket)
            dsl_data = dsl_bytes.decode("utf-8")
            dsl_filename = existing_key
        else:
            # No existing DSL; require an uploaded file
            if not dsl_file:
                raise HTTPException(
                    status_code=400,
                    detail=f"No DSL found for '{simulationName}'. Please upload 'dsl_file'.",
                )
            dsl_data = (await dsl_file.read()).decode("utf-8")
            logger.debug(f"DSL script content:\n{dsl_data}")
            # Save as canonical key
            logger.debug(f"Uploading DSL file to storage: {exact_key}")
            storage.upload_file(
                exact_key, dsl_data.encode("utf-8"), bucket_name=dsl_bucket
            )
            dsl_filename = exact_key

        # Reset persistent event queue for this simulation
        event_store = get_event_store()
        try:
            event_store.purge_all()
        except Exception as purge_exc:
            logger.warning("Failed to purge existing events before init: %s", purge_exc)
        clear_value_cache()
        reset_clock(simulationName)

        # Remember the file we will use (for the current process)
        simulation_controller = get_simulation_controller()
        simulation_controller.dsl_filename = dsl_filename
        try:
            if not _iidm_available(storage, artifact_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"IIDM artifact '{artifact_id}' is missing. Upload IIDM before initializing.",
                )
            simulation_controller.load_dsl_data(dsl_data, simulationName, artifact_id)
        except ValueError as ve:
            logger.error(f"DSL parsing error: {str(ve)}")
            raise HTTPException(
                status_code=400, detail=f"Invalid DSL script: {str(ve)}"
            )
        except AttributeError as ae:
            logger.error(
                f"AttributeError in load_dsl_data, likely due to None context: {str(ae)}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid DSL script: {str(ae)}. Check syntax and grammar.",
            )

        interpreter = simulation_controller.interpreter
        if interpreter is None:
            raise ValueError("Interpreter failed to initialize after loading DSL data.")

        dsl_logger = get_dsl_logger()
        if dsl_logger:
            try:
                await dsl_logger.record_base_script(
                    simulation=simulationName,
                    dsl_text=dsl_data,
                    metadata={
                        "artifact_id": artifact_id,
                        "dsl_filename": simulation_controller.dsl_filename,
                    },
                )
            except Exception:
                logger.debug("Failed to log DSL base script", exc_info=True)

        try:
            set_current_time(simulationName, 0.0)
        except Exception as exc:
            logger.debug("Failed to reset clock for '%s': %s", simulationName, exc)

        sim_config = SimulationConfig(
            simulationName=simulationName,
            startTime=0,
            endTime=interpreter.duration,
            timeStep=interpreter.time_step,
            currentStep=interpreter.current_time,
            actions=[],  # Consider populating from DSL if needed
        )
        payload = sim_config.dict(exclude_none=True)
        logger.debug(f"Validating simulation config: {payload}")
        validate(instance=payload, schema=load_simulation_config_schema())

        bridge = get_nats_bridge()
        if bridge is not None:
            try:
                await bridge.close()
            except Exception as exc:
                logger.debug("Failed to close NATS bridge before reconnect: %s", exc)
            bridge.reset_state()
            try:
                await bridge.connect()
            except Exception as exc:
                logger.warning("Failed to reconnect NATS bridge after init: %s", exc)

        new_keys = getattr(interpreter, "new_measurement_keys", None)
        if new_keys and isinstance(new_keys, (list, set, tuple)):
            # Fire-and-forget subscription requests so init does not block on NATS.
            async def _subscribe_background():
                try:
                    await ensure_measurements_subscribed(
                        new_keys,
                        simulation_name=simulationName,
                        metadata={"source": "dsl"},
                    )
                except Exception:
                    logger.debug("Background subscription failed", exc_info=True)

            asyncio.create_task(_subscribe_background())

        return sim_config
    except ValidationError as ve:
        logger.error(f"Schema validation error: {ve.message}")
        raise HTTPException(
            status_code=422, detail=f"Schema validation error: {ve.message}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initialize simulation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize simulation: {str(e)}"
        )


@router.get("/dsl/simulations")
def list_saved_simulations():
    """Show every DSL stored in the ClickHouse-backed storage.

    Each item includes a friendly `simulationName`, the storage object `path`,
    plus basic metadata like `size`, `lastModified`, and `etag`.
    """
    try:
        storage = _storage_client()
        bucket = storage.dsl_bucket
        items = []
        for obj in storage.list_objects(bucket, recursive=True):
            try:
                name = getattr(obj, "object_name", None)
                if not name or not name.endswith(".dsl"):
                    continue
                base = os.path.basename(name)
                stem = base[:-4]
                # If present, trim legacy suffix "_<uuid32hex>" from the name
                if "_" in stem:
                    head, tail = stem.rsplit("_", 1)
                    if re.fullmatch(r"[0-9a-fA-F]{32}", tail or ""):
                        sim_part = head
                    else:
                        sim_part = stem
                else:
                    sim_part = stem
                simulation_name = sim_part.replace("_", " ")
                items.append(
                    {
                        "simulationName": simulation_name,
                        "path": name,
                        "size": getattr(obj, "size", None),
                        "lastModified": (
                            getattr(obj, "last_modified", None).isoformat()
                            if getattr(obj, "last_modified", None)
                            else None
                        ),
                        "etag": getattr(obj, "etag", None),
                    }
                )
            except Exception:
                continue
        return items
    except StorageError as se:
        logger.error(f"Storage error while listing simulations: {str(se)}")
        raise HTTPException(
            status_code=500,
            detail=f"Storage error while listing simulations: {str(se)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error while listing simulations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/iidm")
def list_saved_iidm():
    """List stored IIDM artifacts with metadata and related object paths."""
    try:
        storage = _storage_client()
        bucket = storage.bucket_name

        artifacts: dict[str, dict] = {}

        for obj in storage.list_objects(bucket, recursive=True):
            name = getattr(obj, "object_name", None)
            if not name or "/" not in name:
                continue

            artifact_id, _, remainder = name.partition("/")
            entry = artifacts.setdefault(
                artifact_id,
                {
                    "artifactId": artifact_id,
                    "description": None,
                    "uploadedAt": None,
                    "iidmPath": None,
                    "networkDataPath": None,
                    "metadataPath": None,
                },
            )

            lower = remainder.lower()
            if lower.endswith((".iidm", ".xiidm", ".xml", ".xz")):
                entry["iidmPath"] = name
                last_mod = getattr(obj, "last_modified", None)
                if last_mod and entry["uploadedAt"] is None:
                    entry["uploadedAt"] = last_mod.isoformat()
            elif lower == "network_data.json":
                entry["networkDataPath"] = name
            elif lower == "metadata.json":
                entry["metadataPath"] = name
                try:
                    meta_bytes = storage.get_file(name)
                    metadata = orjson.loads(meta_bytes)
                    entry["description"] = metadata.get(
                        "description", entry["description"]
                    )
                    if metadata.get("uploaded_at"):
                        entry["uploadedAt"] = metadata["uploaded_at"]
                    if metadata.get("artifact_id"):
                        entry["artifactId"] = metadata["artifact_id"]
                except Exception:
                    pass

        items = [
            value
            for value in artifacts.values()
            if any((value["iidmPath"], value["metadataPath"], value["networkDataPath"]))
        ]
        return JSONResponse(content={"items": items, "count": len(items)})
    except StorageError as se:
        logger.error("Storage error while listing IIDM objects: %s", se)
        raise HTTPException(
            status_code=500, detail=f"Storage error while listing IIDM objects: {se}"
        )
    except Exception as exc:
        logger.error("Unexpected error while listing IIDM objects: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dsl/{simulationName}", response_class=PlainTextResponse)
def get_dsl_file(simulationName: str):
    """Fetch the DSL by simulation name from storage.

    First try the canonical name `<simulationName>.dsl` (spaces become underscores).
    If that doesn't exist, look for the old format `<simulationName>_<uuid>.dsl`.
    If more than one legacy file is found, return 409 to highlight the conflict.
    """
    try:
        storage = _storage_client()
        bucket = storage.dsl_bucket
        normalized_name = simulationName.replace(" ", "_")
        exact_key = f"{normalized_name}.dsl"

        # Try the canonical file name first
        try:
            data = storage.get_file(exact_key, bucket_name=bucket)
            if data is not None:
                return data.decode("utf-8")
        except StorageError as se:
            # If it's truly missing, fall back to the legacy naming scheme
            if getattr(se, "code", "") not in ("NoSuchKey", "NoSuchObject"):
                raise

        # Look for legacy files like '<name>_<uuid>.dsl'
        prefix = f"{normalized_name}_"
        matches = []
        for obj in storage.list_objects(bucket, recursive=True, prefix=prefix):
            name = getattr(obj, "object_name", None)
            if not name or not name.endswith(".dsl"):
                continue
            matches.append(obj)

        if not matches:
            raise HTTPException(
                status_code=404,
                detail=f"No DSL found for simulationName '{simulationName}'.",
            )
        if len(matches) > 1:
            raise HTTPException(
                status_code=409,
                detail=f"Multiple DSLs found for simulationName '{simulationName}'. Please rename to a unique simulationName or clean up duplicates.",
            )

        data = storage.get_file(matches[0].object_name, bucket_name=bucket)
        return data.decode("utf-8")
    except HTTPException:
        raise
    except StorageError as se:
        logger.error(f"Storage error while searching DSL for '{simulationName}': {str(se)}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(se)}")
    except Exception as e:
        logger.error(
            f"Unexpected error while retrieving latest DSL for '{simulationName}': {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dsl/{simulationName}")
def delete_dsl(simulationName: str):
    """Remove the DSL for this simulation from storage.

    Deletes the canonical `<simulationName>.dsl` when it exists. If not, tries the
    legacy `<simulationName>_<uuid>.dsl`. If more than one file matches, returns 409
    so duplicates can be resolved first.
    """
    try:
        storage = _storage_client()
        bucket = storage.dsl_bucket
        normalized_name = simulationName.replace(" ", "_")
        exact_key = f"{normalized_name}.dsl"

        exact_exists = False
        try:
            storage.stat_object(bucket, exact_key)
            exact_exists = True
        except StorageError as se:
            if getattr(se, "code", "") not in ("NoSuchKey", "NoSuchObject"):
                raise

        legacy_matches = []
        if not exact_exists:
            prefix = f"{normalized_name}_"
            for obj in storage.list_objects(bucket, recursive=True, prefix=prefix):
                name = getattr(obj, "object_name", None)
                if not name or not name.endswith(".dsl"):
                    continue
                legacy_matches.append(obj.object_name)
        else:
            # Also check if legacy duplicates exist to keep the name unique
            prefix = f"{normalized_name}_"
            for obj in storage.list_objects(bucket, recursive=True, prefix=prefix):
                name = getattr(obj, "object_name", None)
                if not name or not name.endswith(".dsl"):
                    continue
                legacy_matches.append(obj.object_name)

        total_matches = (1 if exact_exists else 0) + len(legacy_matches)
        if total_matches == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No DSL found for simulationName '{simulationName}'.",
            )
        if total_matches > 1:
            raise HTTPException(
                status_code=409,
                detail=f"Multiple DSLs exist for '{simulationName}'. Please clean duplicates before deleting by name.",
            )

        # Delete the single matching file
        key_to_delete = exact_key if exact_exists else legacy_matches[0]
        storage.remove_object(bucket, key_to_delete)
        return {"message": "DSL deleted", "path": key_to_delete}
    except HTTPException:
        raise
    except StorageError as se:
        logger.error(f"Storage error while deleting DSL for '{simulationName}': {str(se)}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(se)}")
    except Exception as e:
        logger.error(
            f"Unexpected error while deleting DSL for '{simulationName}': {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dsl/{simulationName}")
async def update_dsl(simulationName: str, dsl_file: UploadFile = File(...)):
    """Replace the DSL for this simulation using a file upload (multipart/form-data).

    Expects form field `dsl_file`. If only a single legacy file exists, it is
    replaced with the canonical `<simulationName>.dsl`. If multiple legacy files
    are found, returns 409 to avoid ambiguity.
    """
    try:
        dsl_bytes = await dsl_file.read()
        if not dsl_bytes:
            raise HTTPException(
                status_code=400, detail="Uploaded file is empty or missing"
            )

        storage = _storage_client()
        bucket = storage.dsl_bucket
        normalized_name = simulationName.replace(" ", "_")
        exact_key = f"{normalized_name}.dsl"

        exact_exists = False
        try:
            storage.stat_object(bucket, exact_key)
            exact_exists = True
        except StorageError as se:
            if getattr(se, "code", "") not in ("NoSuchKey", "NoSuchObject"):
                raise

        # Gather any legacy files for the same name
        legacy_matches = []
        prefix = f"{normalized_name}_"
        for obj in storage.list_objects(bucket, recursive=True, prefix=prefix):
            name = getattr(obj, "object_name", None)
            if not name or not name.endswith(".dsl"):
                continue
            legacy_matches.append(obj.object_name)

        total_matches = (1 if exact_exists else 0) + len(legacy_matches)
        if total_matches > 1 and not exact_exists:
            # Multiple legacy candidates -> conflict to keep naming unambiguous
            raise HTTPException(
                status_code=409,
                detail=f"Multiple legacy DSLs exist for '{simulationName}'. Please clean duplicates before updating.",
            )

        # If there's exactly one legacy file, drop it first and write the canonical file
        if not exact_exists and len(legacy_matches) == 1:
            try:
                storage.remove_object(bucket, legacy_matches[0])
            except Exception:
                pass

        # Write or overwrite the canonical file
        storage.upload_file(exact_key, dsl_bytes, bucket_name=bucket)
        return {"message": "DSL updated", "path": exact_key}
    except HTTPException:
        raise
    except StorageError as se:
        logger.error(f"Storage error while updating DSL for '{simulationName}': {str(se)}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(se)}")
    except Exception as e:
        logger.error(
            f"Unexpected error while updating DSL for '{simulationName}': {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))
