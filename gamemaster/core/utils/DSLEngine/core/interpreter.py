"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional

from antlr4 import CommonTokenStream, InputStream

from ..antlr.PowerEventDSLLexer import PowerEventDSLLexer
from ..antlr.PowerEventDSLParser import PowerEventDSLParser
from ..function_registry import FunctionDefinition, load_functions, store_functions
from ..resolvers.cluster_resolver import ClusterResolver
from ..iidm.properties import get_iidm_properties
from ..simulation.action_processor import ActionProcessor as AP
from ..simulation.engine import (
    start_simulation as _start,
    get_current_step_actions as _step,
)
from ..persistence.event_store import build_action_payload
from ..visitors.statement_visitor import StatementVisitorMixin
from ..visitors.action_visitor import ActionVisitorMixin
from ..visitors.target_visitor import TargetVisitorMixin
from ..visitors.expression_visitor import ExpressionVisitorMixin


logger = logging.getLogger(__name__)


class DSLInterpreter(
    StatementVisitorMixin,
    ActionVisitorMixin,
    TargetVisitorMixin,
    ExpressionVisitorMixin,
):
    def __init__(
        self,
        artifact_id,
        event_store=None,
        simulation_name: Optional[str] = None,
        event_source: str = "dsl",
        *,
        commit_registry: bool = True,
        inherited_functions: Optional[Dict[str, FunctionDefinition]] = None,
        call_stack: Optional[list[str]] = None,
        retain_pending_requests: bool = False,
    ):
        self.artifact_id = artifact_id
        self.duration = None
        self.time_step = None
        self.time_events = []
        self.condition_events = []
        self.dependent_events = []
        self.current_time = 0.0
        self.completed_events = set()
        self.labels = {}
        self.iidm_cache = {}
        self.event_store = event_store
        self.simulation_name = simulation_name
        self.event_source = event_source
        self.new_measurement_keys: set[str] = set()
        self.functions: Dict[str, FunctionDefinition] = dict(
            inherited_functions or load_functions(simulation_name)
        )
        self._staged_functions: Dict[str, FunctionDefinition] = {}
        self._transaction_active = False
        self._pending_persist_requests: list[dict[str, Any]] = []
        self._transaction_snapshot: dict[str, Any] = {}
        self._commit_registry = commit_registry
        self._retain_pending_requests = retain_pending_requests
        self._template_bindings_stack: list[dict[str, dict[str, Any]]] = []
        self._call_stack: list[str] = list(call_stack or [])
        self._function_invocation_counter = 0
        self._function_completion_children: dict[str, set[str]] = {}
        self._function_completion_waiters: dict[str, set[str]] = {}
        self.cluster_resolver = ClusterResolver(
            self.artifact_id, self.iidm_cache, get_iidm_properties
        )
        logger.debug("DSLInterpreter initialized with artifact_id: %s", artifact_id)

    def _epsilon(self) -> float:
        try:
            ts = float(self.time_step or 0.0)
        except Exception:
            ts = 0.0
        return max(1e-3, ts / 10.0) if ts > 0 else 1e-3

    def prepare_action(self, action: dict, system_state: Optional[dict] = None) -> dict:
        return AP.prepare_action(
            action,
            system_state or {},
            materialize_target=self._materialize_target,
            normalize_targets=self._normalize_targets,
        )

    def get_current_step_actions(self, new_time: float, system_state=None):
        return _step(self, new_time, system_state)

    def start_simulation(self):
        return _start(self)

    def get_current_status(self, system_state=None):
        if system_state is None:
            system_state = {}
        current_actions = []
        eps = self._epsilon()
        for event in self.time_events:
            ts = event["time_spec"]
            if isinstance(ts, dict) and "interval" in ts:
                start, end = ts["interval"]
                if start <= self.current_time <= end:
                    current_actions.append(event["action"])
            elif abs(ts - self.current_time) < max(eps, (self.time_step or 0) / 2):
                current_actions.append(event["action"])
        for event in self.condition_events:
            if self.evaluate_dynamic_expression(event["dynamic_expr"], system_state):
                current_actions.append(event["action"])
        for event in self.dependent_events:
            if event["dependency"] in self.completed_events:
                current_actions.append(event["action"])
        status = "running" if self.current_time < self.duration else "simulation_ended"
        logger.debug(
            "Current status: time=%s, actions=%s, status=%s",
            self.current_time,
            current_actions,
            status,
        )
        return {
            "current_time": self.current_time,
            "actions": current_actions,
            "status": status,
        }

    # Back-compat for services calling interpreter._build_action_payload
    def _build_action_payload(self, action: dict) -> dict:
        return build_action_payload(action)

    def _begin_transaction(self) -> None:
        self._transaction_active = True
        self._pending_persist_requests = []
        self._staged_functions = {}
        self._transaction_snapshot = {
            "time_events": list(self.time_events),
            "condition_events": list(self.condition_events),
            "dependent_events": list(self.dependent_events),
            "labels": dict(self.labels),
            "functions": dict(self.functions),
            "new_measurement_keys": set(self.new_measurement_keys),
            "function_completion_children": {
                key: set(value) for key, value in self._function_completion_children.items()
            },
            "function_completion_waiters": {
                key: set(value) for key, value in self._function_completion_waiters.items()
            },
        }

    def _rollback_transaction(self) -> None:
        snapshot = self._transaction_snapshot or {}
        self.time_events = list(snapshot.get("time_events", []))
        self.condition_events = list(snapshot.get("condition_events", []))
        self.dependent_events = list(snapshot.get("dependent_events", []))
        self.labels = dict(snapshot.get("labels", {}))
        self.functions = dict(snapshot.get("functions", {}))
        self.new_measurement_keys = set(snapshot.get("new_measurement_keys", set()))
        self._function_completion_children = {
            key: set(value)
            for key, value in snapshot.get("function_completion_children", {}).items()
        }
        self._function_completion_waiters = {
            key: set(value)
            for key, value in snapshot.get("function_completion_waiters", {}).items()
        }
        self._pending_persist_requests = []
        self._staged_functions = {}
        self._transaction_snapshot = {}
        self._transaction_active = False

    def _commit_transaction(self) -> None:
        if self.event_store is not None:
            for request in self._pending_persist_requests:
                self.event_store.enqueue_event(**request)
        if self._commit_registry and self._staged_functions:
            store_functions(self.simulation_name, self._staged_functions)
        if not self._retain_pending_requests:
            self._pending_persist_requests = []
        self._staged_functions = {}
        self._transaction_snapshot = {}
        self._transaction_active = False

    def _resolve_binding(self, name: str) -> dict[str, Any]:
        for scope in reversed(self._template_bindings_stack):
            if name in scope:
                return scope[name]
        raise ValueError(f"Identifier '{name}' is not defined in this context")

    def _resolve_identifier_value(self, name: str) -> Any:
        return self._resolve_binding(name)["value"]

    def _resolve_identifier_source(self, name: str) -> str:
        return str(self._resolve_binding(name)["source"])

    def _push_template_bindings(self, bindings: dict[str, dict[str, Any]]) -> None:
        self._template_bindings_stack.append(bindings)

    def _pop_template_bindings(self) -> None:
        if self._template_bindings_stack:
            self._template_bindings_stack.pop()

    def _register_function(self, definition: FunctionDefinition) -> None:
        self.functions[definition.name] = definition
        self._staged_functions[definition.name] = definition

    def _lookup_function(self, name: str) -> FunctionDefinition:
        definition = self.functions.get(name)
        if definition is None:
            raise ValueError(f"Function '{name}' is not defined")
        return definition

    @staticmethod
    def _new_completion_event_id() -> str:
        return str(uuid.uuid4())

    def _register_function_completion(
        self,
        completion_event_id: Optional[str],
        child_event_ids,
    ) -> set[str]:
        if not completion_event_id:
            return set()
        remaining = self._function_completion_children.setdefault(completion_event_id, set())
        for child_event_id in child_event_ids or []:
            if not child_event_id:
                continue
            child_event_id = str(child_event_id)
            if child_event_id in self.completed_events:
                continue
            remaining.add(child_event_id)
            self._function_completion_waiters.setdefault(child_event_id, set()).add(
                completion_event_id
            )
        if remaining:
            return set()
        self._function_completion_children.pop(completion_event_id, None)
        return {completion_event_id}

    def _resolve_function_completion_ids(self, completed_event_id: Optional[str]) -> list[str]:
        if not completed_event_id:
            return []
        parents = self._function_completion_waiters.pop(str(completed_event_id), set())
        completed_aliases: list[str] = []
        for parent_id in parents:
            remaining = self._function_completion_children.get(parent_id)
            if remaining is None:
                continue
            remaining.discard(str(completed_event_id))
            if remaining:
                continue
            self._function_completion_children.pop(parent_id, None)
            completed_aliases.append(parent_id)
        return completed_aliases

    def _next_invocation_prefix(self, function_name: str) -> str:
        self._function_invocation_counter += 1
        return f"__fn_{function_name}_{self._function_invocation_counter}"

    def _persist_event(
        self,
        *,
        event_id: str,
        action: dict,
        time_spec: str,
        at: float | None = None,
        interval_start: float | None = None,
        interval_end: float | None = None,
        law: str | None = None,
        condition_expr=None,
        dependency_id: str | None = None,
        due_at: float | None = None,
        tag: str | None = None,
        status: str | None = None,
    ) -> None:
        evt_type = action.get("type", "unknown")
        target = action.get("id") if "id" in action else action.get("target")
        payload = self._build_action_payload(action)
        metadata = action.get("metadata") if isinstance(action, dict) else None

        def _normalize_target(value):
            if isinstance(value, list):
                try:
                    return ",".join(sorted(map(str, value)))
                except Exception:
                    return ",".join(map(str, value))
            return str(value)

        idempotency_target = _normalize_target(target)
        if evt_type == "change_network_characteristics":
            canonical = {
                "links": payload.get("links"),
                "nodes": payload.get("nodes"),
                "delay_function": payload.get("delay_function"),
                "drop_function": payload.get("drop_function"),
                "corruption_functions": payload.get("corruption_functions"),
                "t_start": payload.get("t_start"),
                "t_start_from_now": payload.get("t_start_from_now"),
            }
            idempotency_target = json.dumps(canonical, sort_keys=True, default=str)

        idempotency_key = (
            f"dsl:{self.simulation_name}:{evt_type}:{idempotency_target}:"
            f"{at or interval_start}:{interval_end or ''}:{law or ''}:"
            f"{dependency_id or ''}:{tag or ''}"
        )

        status_override = status
        if time_spec == "point" and dependency_id and at is None:
            status_override = "pending"

        computed_due_at = due_at
        if computed_due_at is None and time_spec in {"point", "interval"}:
            lead = getattr(self, "time_step", None)
            try:
                lead_val = float(lead) if lead is not None else 0.0
            except (TypeError, ValueError):
                lead_val = 0.0
            if lead_val <= 0:
                lead_val = 1e-3
            anchor = at if time_spec == "point" else interval_start
            if anchor is not None:
                computed_due_at = max(0.0, float(anchor) - lead_val)

        request = {
            "source": self.event_source,
            "type": evt_type,
            "target": target,
            "payload": payload or None,
            "metadata": metadata,
            "time_spec": time_spec,
            "at": at,
            "interval_start": interval_start,
            "interval_end": interval_end,
            "law": law,
            "condition_expr": condition_expr,
            "dependency_id": dependency_id,
            "priority": 0,
            "idempotency_key": idempotency_key,
            "status": status_override,
            "event_id": event_id,
            "simulation": self.simulation_name,
            "due_at": computed_due_at,
            "tag": tag,
        }

        if self._transaction_active:
            self._pending_persist_requests.append(request)
            return
        if self.event_store is not None:
            self.event_store.enqueue_event(**request)

    def _update_pending_event(
        self,
        event_id: str,
        *,
        payload: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> bool:
        if not self._transaction_active:
            return False
        for request in reversed(self._pending_persist_requests):
            if request.get("event_id") != event_id:
                continue
            if payload is not None:
                request["payload"] = payload
            if status is not None:
                request["status"] = status
            return True
        return False

    def _clone_for_expansion(self, *, call_name: str) -> "DSLInterpreter":
        clone = DSLInterpreter(
            self.artifact_id,
            event_store=None,
            simulation_name=self.simulation_name,
            event_source=self.event_source,
            commit_registry=False,
            inherited_functions=self.functions,
            call_stack=self._call_stack + [call_name],
            retain_pending_requests=True,
        )
        clone.duration = self.duration
        clone.time_step = self.time_step
        clone.current_time = self.current_time
        clone.labels = dict(self.labels)
        clone.iidm_cache = self.iidm_cache
        clone.cluster_resolver.cache = self.iidm_cache
        clone.new_measurement_keys = set(self.new_measurement_keys)
        clone._function_invocation_counter = self._function_invocation_counter
        clone._function_completion_children = {}
        clone._function_completion_waiters = {}
        return clone

    def _merge_completion_state(self, child: "DSLInterpreter") -> None:
        self.completed_events.update(getattr(child, "completed_events", set()))
        for key, value in getattr(child, "_function_completion_children", {}).items():
            self._function_completion_children.setdefault(key, set()).update(value)
        for key, value in getattr(child, "_function_completion_waiters", {}).items():
            self._function_completion_waiters.setdefault(key, set()).update(value)

    def _merge_child(self, child: "DSLInterpreter") -> None:
        self.time_events.extend(child.time_events)
        self.condition_events.extend(child.condition_events)
        self.dependent_events.extend(child.dependent_events)
        self.labels.update(child.labels)
        self.new_measurement_keys.update(child.new_measurement_keys)
        self._merge_completion_state(child)
        self._pending_persist_requests.extend(child._pending_persist_requests)
        self._function_invocation_counter = max(
            self._function_invocation_counter,
            child._function_invocation_counter,
        )

    def _parse_program(self, text: str):
        stream = InputStream(text)
        lexer = PowerEventDSLLexer(stream)
        token_stream = CommonTokenStream(lexer)
        parser = PowerEventDSLParser(token_stream)
        return parser.program()


__all__ = ["DSLInterpreter"]
