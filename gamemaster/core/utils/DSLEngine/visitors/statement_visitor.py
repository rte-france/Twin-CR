"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

import copy
import uuid
from typing import Any, Dict, Iterable, Optional

from antlr4 import InputStream, ParserRuleContext

from ..antlr.PowerEventDSLLexer import PowerEventDSLLexer
from ..antlr.PowerEventDSLVisitor import PowerEventDSLVisitor
from ..core.time_utils import to_seconds
from ..function_registry import FunctionDefinition


class StatementVisitorMixin(PowerEventDSLVisitor):
    @staticmethod
    def _ctx_text(ctx: ParserRuleContext) -> str:
        """Return the original DSL slice for this context, preserving spaces when available."""
        try:
            stream = ctx.start.getInputStream()
            if stream:
                return stream.getText(ctx.start.start, ctx.stop.stop)
        except Exception:
            pass
        return ctx.getText()

    @staticmethod
    def _quote_string(value: str) -> str:
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    @staticmethod
    def _format_seconds(value: float) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return str(value)
        if abs(numeric - round(numeric)) < 1e-9:
            return str(int(round(numeric)))
        return f"{numeric:g}"

    def _resolve_now(self) -> float:
        try:
            base_time = float(getattr(self, "current_time", 0.0))
        except (TypeError, ValueError):
            base_time = 0.0
        try:
            step = getattr(self, "time_step", None)
            step_val = float(step) if step is not None else 1.0
        except (TypeError, ValueError):
            step_val = 1.0
        if step_val <= 0:
            step_val = 1.0
        return base_time + step_val

    def _priority_rank(self, source: Optional[str]) -> int:
        ranks = {
            "dsl": 3,
            "trainer": 2,
            "user": 1,
            "user_dsl": 1,
        }
        return ranks.get(str(source or "").lower(), 0)

    def _resolve_existing_store(self):
        if self.event_store is not None and hasattr(self.event_store, "list_events"):
            return self.event_store
        try:
            from ...domain.controllers.global_instances import get_event_store

            return get_event_store()
        except Exception:
            return None

    def _conflict_keys_from_action(
        self, action: dict, scheduled_at: Optional[float]
    ) -> list[tuple[str, str, float]]:
        if scheduled_at is None or not isinstance(action, dict):
            return []
        action_type = str(action.get("type") or "")
        targets: Iterable[Any]
        if action_type == "change_network_characteristics":
            targets = []
            for link in action.get("links") or []:
                if not isinstance(link, dict):
                    continue
                src = link.get("from")
                dst = link.get("to")
                if src is None or dst is None:
                    continue
                targets.append(f"link:{src}->{dst}")
            for node in action.get("nodes") or []:
                if node is None:
                    continue
                targets.append(f"node:{node}")
            if not targets:
                targets = ["network"]
        else:
            targets = action.get("targets") or []
            if isinstance(targets, str):
                targets = [targets]
            if not targets:
                single = action.get("target")
                if single is None:
                    single = action.get("id")
                targets = [single] if single is not None else []
        return [
            (str(target), action_type, float(scheduled_at))
            for target in targets
            if target is not None
        ]

    def _conflict_keys_from_store_event(self, event: dict) -> list[tuple[str, str, float]]:
        scheduled_at = event.get("at")
        if scheduled_at is None:
            scheduled_at = event.get("interval_start")
        try:
            when = float(scheduled_at)
        except (TypeError, ValueError):
            return []
        action_type = str(event.get("type") or "")
        target = event.get("target")
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        if action_type == "change_network_characteristics":
            targets = []
            for link in payload.get("links") or []:
                if not isinstance(link, dict):
                    continue
                src = link.get("from")
                dst = link.get("to")
                if src is None or dst is None:
                    continue
                targets.append(f"link:{src}->{dst}")
            for node in payload.get("nodes") or []:
                if node is None:
                    continue
                targets.append(f"node:{node}")
            if not targets:
                targets = ["network"]
        else:
            targets = payload.get("targets")
            if isinstance(targets, str):
                targets = [targets]
            if not targets:
                if target is not None:
                    targets = [target]
                else:
                    targets = []
        return [
            (str(item), action_type, when)
            for item in targets
            if item is not None
        ]

    def _validate_checked_batch(self, child) -> None:
        current_rank = self._priority_rank(getattr(self, "event_source", None))
        batch_keys: set[tuple[str, str, float]] = set()
        for entry in getattr(child, "time_events", []) or []:
            time_spec = entry.get("time_spec")
            scheduled_at = None
            if isinstance(time_spec, dict) and "interval" in time_spec:
                scheduled_at = time_spec["interval"][0]
            else:
                scheduled_at = time_spec
            keys = self._conflict_keys_from_action(entry.get("action"), scheduled_at)
            for key in keys:
                if key in batch_keys:
                    raise ValueError(
                        "checkAndApply rejected the function because it expands to conflicting actions."
                    )
                batch_keys.add(key)

        store = self._resolve_existing_store()
        if store is None or current_rank >= self._priority_rank("dsl"):
            return
        try:
            existing = store.list_events(
                simulation=self.simulation_name,
                limit=100000,
                offset=0,
            )
        except Exception:
            return

        higher_priority_keys: set[tuple[str, str, float]] = set()
        for event in existing:
            status = str(event.get("status") or "").lower()
            if status not in {"pending", "scheduled", "active", "locked"}:
                continue
            if self._priority_rank(event.get("source")) <= current_rank:
                continue
            for key in self._conflict_keys_from_store_event(event):
                higher_priority_keys.add(key)

        overlap = batch_keys & higher_priority_keys
        if overlap:
            raise ValueError(
                "checkAndApply rejected the function because it conflicts with a higher-priority action."
            )

    def _substitute_identifiers(
        self, text: str, bindings: dict[str, dict[str, Any]]
    ) -> str:
        if not text or not bindings:
            return text
        lexer = PowerEventDSLLexer(InputStream(text))
        parts: list[str] = []
        cursor = 0
        for token in lexer.getAllTokens():
            start = getattr(token, "start", None)
            stop = getattr(token, "stop", None)
            if start is None or stop is None:
                continue
            parts.append(text[cursor:start])
            replacement = text[start : stop + 1]
            if (
                token.type == PowerEventDSLLexer.IDENTIFIER
                and token.text in bindings
            ):
                replacement = str(bindings[token.text]["source"])
            parts.append(replacement)
            cursor = stop + 1
        parts.append(text[cursor:])
        return "".join(parts)

    def _call_arg_binding(self, ctx) -> dict[str, Any]:
        raw = self._ctx_text(ctx)
        if ctx.target():
            value = self.visit(ctx.target())
        elif ctx.timeValue():
            value = self.visit(ctx.timeValue())
        elif ctx.signedNumericAtom():
            value = self.visit(ctx.signedNumericAtom())
        elif ctx.booleanLiteral():
            value = self.visit(ctx.booleanLiteral())
        else:
            value = raw
        return {"source": raw, "value": value}

    def _bind_call_arguments(self, call_ctx, definition: FunctionDefinition):
        args = list(call_ctx.callArgList().callArg()) if call_ctx.callArgList() else []
        positional = []
        named: dict[str, dict[str, Any]] = {}
        named_section_started = False

        for arg in args:
            value_ctx = arg.callArgValue()
            binding = self._call_arg_binding(value_ctx)
            identifier_node = arg.IDENTIFIER()
            if identifier_node is not None:
                named_section_started = True
                key = identifier_node.getText()
                if key in named:
                    raise ValueError(f"Argument '{key}' was provided more than once")
                named[key] = binding
            else:
                if named_section_started:
                    raise ValueError(
                        f"Function '{definition.name}' cannot receive positional arguments after named arguments"
                    )
                positional.append(binding)

        bindings: dict[str, dict[str, Any]] = {}
        for index, param in enumerate(definition.params):
            if index < len(positional):
                if param in named:
                    raise ValueError(f"Argument '{param}' was provided more than once")
                bindings[param] = positional[index]
                continue
            if param in named:
                bindings[param] = named.pop(param)

        if len(positional) > len(definition.params):
            raise ValueError(
                f"Function '{definition.name}' received too many positional arguments"
            )
        if named:
            unknown = ", ".join(sorted(named))
            raise ValueError(
                f"Function '{definition.name}' received unexpected named arguments: {unknown}"
            )
        missing = [param for param in definition.params if param not in bindings]
        if missing:
            raise ValueError(
                f"Function '{definition.name}' is missing arguments: {', '.join(missing)}"
            )
        return bindings

    @staticmethod
    def _function_child_event_ids(child) -> list[str]:
        event_ids: list[str] = []
        for collection_name in ("time_events", "condition_events", "dependent_events"):
            for event in getattr(child, collection_name, []) or []:
                event_id = event.get("id") if isinstance(event, dict) else None
                if event_id:
                    event_ids.append(str(event_id))
        return event_ids

    @staticmethod
    def _prune_completed_child_events(child) -> None:
        completed = set(getattr(child, "completed_events", set()) or set())
        if not completed:
            return
        child.time_events = [
            event
            for event in getattr(child, "time_events", []) or []
            if event.get("id") not in completed
        ]
        child.condition_events = [
            event
            for event in getattr(child, "condition_events", []) or []
            if event.get("id") not in completed
        ]
        child.dependent_events = [
            event
            for event in getattr(child, "dependent_events", []) or []
            if event.get("id") not in completed
        ]

    def _build_invocation_action(
        self,
        *,
        function_name: str,
        bindings: dict[str, dict[str, Any]],
        checked: bool,
        completion_event_id: Optional[str] = None,
    ) -> dict[str, Any]:
        action = {
            "type": "invoke_function",
            "function_name": function_name,
            "bindings": copy.deepcopy(bindings),
            "checked": bool(checked),
        }
        if completion_event_id:
            action["completion_event_id"] = str(completion_event_id)
        return action

    def _build_function_completion_action(
        self,
        *,
        function_name: str,
        child_event_ids: Optional[Iterable[str]] = None,
        expanded: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        action = {
            "type": "function_completion",
            "function_name": function_name,
            "child_event_ids": [str(event_id) for event_id in (child_event_ids or []) if event_id],
            "expanded": bool(expanded),
        }
        if metadata:
            action["metadata"] = dict(metadata)
        return action

    def _persist_function_completion_marker(
        self,
        *,
        completion_event_id: Optional[str],
        function_name: str,
        tag: Optional[str],
    ) -> None:
        if not completion_event_id:
            return
        metadata = {
            "event_id": str(completion_event_id),
            "function_name": function_name,
        }
        if tag:
            metadata["invocation_tag"] = tag
        action = self._build_function_completion_action(
            function_name=function_name,
            child_event_ids=[],
            expanded=False,
            metadata=metadata,
        )
        request = {
            "source": "system",
            "type": action["type"],
            "target": None,
            "payload": self._build_action_payload(action) or None,
            "metadata": action.get("metadata"),
            "time_spec": "point",
            "at": None,
            "interval_start": None,
            "interval_end": None,
            "law": None,
            "condition_expr": None,
            "dependency_id": None,
            "priority": 0,
            "idempotency_key": None,
            "status": "pending",
            "event_id": str(completion_event_id),
            "simulation": self.simulation_name,
            "due_at": None,
            "tag": tag,
        }
        if self._transaction_active:
            self._pending_persist_requests.append(request)
            return
        if self.event_store is not None:
            self.event_store.enqueue_event(**request)

    def _update_function_completion_marker(
        self,
        *,
        completion_event_id: Optional[str],
        function_name: str,
        child_event_ids: Optional[Iterable[str]] = None,
        expanded: bool = True,
    ) -> None:
        if not completion_event_id:
            return
        payload = {
            "function_name": function_name,
            "child_event_ids": [str(event_id) for event_id in (child_event_ids or []) if event_id],
            "expanded": bool(expanded),
        }
        completed_immediately = bool(expanded and not payload["child_event_ids"])
        updated = self._update_pending_event(
            str(completion_event_id),
            payload=payload,
            status="completed" if completed_immediately else None,
        )
        if not updated and self.event_store is not None:
            try:
                self.event_store.update_payload(str(completion_event_id), payload)
            except Exception:
                pass
            if completed_immediately:
                try:
                    self.event_store.mark_completed([str(completion_event_id)])
                except Exception:
                    pass
        if completed_immediately:
            self.completed_events.add(str(completion_event_id))

    def _local_tag_mapping(self, definition: FunctionDefinition, bindings) -> dict[str, str]:
        prefix = self._next_invocation_prefix(definition.name)
        mapping: dict[str, str] = {}
        self._push_template_bindings(bindings)
        try:
            for statement in definition.statements:
                if not statement.tagged():
                    continue
                tag = self.visit(statement.tagged().stringAtom())
                if tag not in mapping:
                    mapping[tag] = f"{prefix}_{tag}"
        finally:
            self._pop_template_bindings()
        return mapping

    def _rewrite_function_statement(
        self,
        statement_ctx,
        *,
        bindings: dict[str, dict[str, Any]],
        invocation_time: float,
        local_tags: dict[str, str],
    ) -> str:
        executable_text = self._substitute_identifiers(
            self._ctx_text(statement_ctx.executable()),
            bindings,
        )
        tagged_suffix = ""

        self._push_template_bindings(bindings)
        try:
            if statement_ctx.tagged():
                raw_tag = self.visit(statement_ctx.tagged().stringAtom())
                resolved_tag = local_tags.get(raw_tag, raw_tag)
                tagged_suffix = f" tagged {self._quote_string(resolved_tag)}"

            first_child = statement_ctx.getChild(0).getText()
            if first_child == "at":
                relative = self.visit(statement_ctx.relativeTimeSpec())
                if isinstance(relative, dict) and "interval" in relative:
                    start, end = relative["interval"]
                    time_text = (
                        f"[{self._format_seconds(invocation_time + start)} seconds, "
                        f"{self._format_seconds(invocation_time + end)} seconds]"
                    )
                    law = relative.get("law")
                    if law:
                        time_text += f" with law {law if law == 'linear' else self._quote_string(law)}"
                else:
                    time_text = (
                        f"{self._format_seconds(invocation_time + float(relative))} seconds"
                    )
                return f"at {time_text}, {executable_text}{tagged_suffix};"

            if first_child == "when":
                condition_text = self._substitute_identifiers(
                    self._ctx_text(statement_ctx.dynamicExpression()),
                    bindings,
                )
                return f"when {condition_text}, {executable_text}{tagged_suffix};"

            dependency = self.visit(statement_ctx.stringAtom())
            dependency = local_tags.get(dependency, dependency)
            return (
                f"after {self._quote_string(dependency)} is completed, "
                f"{executable_text}{tagged_suffix};"
            )
        finally:
            self._pop_template_bindings()

    def _expand_function_invocation(
        self,
        *,
        function_name: str,
        bindings: dict[str, dict[str, Any]],
        invocation_time: float,
        checked: bool,
        completion_event_id: Optional[str] = None,
        execute_now: bool = False,
        system_state: Optional[dict] = None,
    ) -> tuple[list[Any], set[str]]:
        if getattr(self, "event_source", None) == "user_dsl":
            raise ValueError("Function definitions and calls are not supported in atomic DSL updates.")
        if function_name in getattr(self, "_call_stack", []):
            raise ValueError(f"Recursive function invocation detected for '{function_name}'")

        definition = self._lookup_function(function_name)
        local_tags = self._local_tag_mapping(definition, bindings)

        expanded_statements = [
            self._rewrite_function_statement(
                statement,
                bindings=bindings,
                invocation_time=invocation_time,
                local_tags=local_tags,
            )
            for statement in definition.statements
        ]
        expanded_program = "\n".join(expanded_statements).strip()
        if not expanded_program:
            self._update_function_completion_marker(
                completion_event_id=completion_event_id,
                function_name=function_name,
                child_event_ids=[],
                expanded=True,
            )
            immediate_completion_ids = self._register_function_completion(
                completion_event_id,
                [],
            )
            if immediate_completion_ids:
                self.completed_events.update(immediate_completion_ids)
            return [], immediate_completion_ids

        child = self._clone_for_expansion(call_name=function_name)
        tree = child._parse_program(expanded_program)
        child.visit(tree)

        if checked:
            self._validate_checked_batch(child)

        child_event_ids = self._function_child_event_ids(child)
        self._update_function_completion_marker(
            completion_event_id=completion_event_id,
            function_name=function_name,
            child_event_ids=child_event_ids,
            expanded=True,
        )
        immediate_actions: list[Any] = []
        if execute_now:
            child.current_time = invocation_time
            result = child.get_current_step_actions(
                invocation_time,
                system_state=system_state,
            )
            immediate_actions = list(result.get("actions") or [])
            self._prune_completed_child_events(child)

        self._merge_child(child)
        immediate_completion_ids = self._register_function_completion(
            completion_event_id,
            child_event_ids,
        )
        if immediate_completion_ids:
            self.completed_events.update(immediate_completion_ids)
        return immediate_actions, immediate_completion_ids

    def _expand_function_call(
        self,
        call_ctx,
        *,
        invocation_time: float,
        checked: bool,
        completion_event_id: Optional[str] = None,
        execute_now: bool = False,
        system_state: Optional[dict] = None,
    ) -> list[Any]:
        function_name = call_ctx.IDENTIFIER().getText()
        definition = self._lookup_function(function_name)
        bindings = self._bind_call_arguments(call_ctx, definition)
        return self._expand_function_invocation(
            function_name=function_name,
            bindings=bindings,
            invocation_time=invocation_time,
            checked=checked,
            completion_event_id=completion_event_id,
            execute_now=execute_now,
            system_state=system_state,
        )

    def _invoke_function_action(
        self,
        action: dict[str, Any],
        *,
        invocation_time: float,
        system_state: Optional[dict] = None,
    ) -> list[Any]:
        if not isinstance(action, dict):
            return []
        function_name = str(action.get("function_name") or "")
        bindings = action.get("bindings") or {}
        if not function_name or not isinstance(bindings, dict):
            raise ValueError("Invalid invoke_function action payload")
        immediate_actions, immediate_completion_ids = self._expand_function_invocation(
            function_name=function_name,
            bindings=bindings,
            invocation_time=invocation_time,
            checked=bool(action.get("checked")),
            completion_event_id=action.get("completion_event_id"),
            execute_now=True,
            system_state=system_state,
        )
        return {
            "actions": immediate_actions,
            "completed_ids": immediate_completion_ids,
        }

    def _build_function_definition(self, ctx) -> FunctionDefinition:
        name = ctx.IDENTIFIER().getText()
        params = []
        if ctx.functionParamList():
            params = [token.getText() for token in ctx.functionParamList().IDENTIFIER()]
        statements = tuple(ctx.functionStatement() or [])
        source_text = "\n".join(self._ctx_text(statement) for statement in statements)
        return FunctionDefinition(
            name=name,
            params=params,
            statements=statements,
            source_text=source_text,
        )

    def visitProgram(self, ctx):
        self._begin_transaction()
        try:
            for statement in ctx.statement() or []:
                if not statement.functionDef():
                    continue
                if getattr(self, "event_source", None) == "user_dsl":
                    raise ValueError(
                        "Function definitions are not supported in atomic DSL updates."
                    )
                definition = self._build_function_definition(statement.functionDef())
                if definition.name in self.functions:
                    raise ValueError(
                        f"Function '{definition.name}' is already defined for this simulation"
                    )
                self._register_function(definition)

            for statement in ctx.statement() or []:
                if statement.functionDef():
                    continue
                self.visit(statement)
        except Exception:
            self._rollback_transaction()
            raise
        self._commit_transaction()
        return None

    def visitFunctionDef(self, ctx):
        if getattr(self, "event_source", None) == "user_dsl":
            raise ValueError("Function definitions are not supported in atomic DSL updates.")
        definition = self._build_function_definition(ctx)
        if definition.name in self.functions:
            raise ValueError(f"Function '{definition.name}' is already defined")
        self._register_function(definition)
        return definition

    def visitStringAtom(self, ctx):
        if ctx.STRING():
            return ctx.STRING().getText()[1:-1]
        return str(self._resolve_identifier_value(ctx.IDENTIFIER().getText()))

    def visitNumericAtom(self, ctx):
        if ctx.NUMBER():
            return float(ctx.NUMBER().getText())
        value = self._resolve_identifier_value(ctx.IDENTIFIER().getText())
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Identifier '{ctx.IDENTIFIER().getText()}' does not resolve to a numeric value"
            ) from exc

    def visitSignedNumericAtom(self, ctx):
        value = self.visit(ctx.numericAtom())
        sign = ctx.getChild(0).getText()
        if sign == "-":
            return -float(value)
        return float(value)

    def visitSetDuration(self, ctx):
        if self.duration is not None:
            raise ValueError("Duration already set")
        self.duration = self.visit(ctx.timeValue())

    def visitSetTimeStep(self, ctx):
        if self.time_step is not None:
            raise ValueError("Time step already set")
        self.time_step = self.visit(ctx.timeValue())

    def visitExecutable(self, ctx):
        return self.visit(ctx.getChild(0))

    def visitEventDef(self, ctx):
        event_id = str(uuid.uuid4())
        tag = self.visit(ctx.tagged().stringAtom()) if ctx.tagged() else None
        executable_ctx = ctx.executable()
        first_child = ctx.getChild(0).getText()

        call_ctx = None
        checked = False
        if executable_ctx.callExpr():
            call_ctx = executable_ctx.callExpr()
        elif executable_ctx.verifiedCallExpr():
            call_ctx = executable_ctx.verifiedCallExpr().callExpr()
            checked = True

        completion_event_id = None
        if call_ctx is not None and tag:
            completion_event_id = self._new_completion_event_id()
            self.labels[tag] = completion_event_id

        if call_ctx is not None:
            function_name = call_ctx.IDENTIFIER().getText()
            definition = self._lookup_function(function_name)
            bindings = self._bind_call_arguments(call_ctx, definition)
            if completion_event_id:
                self._persist_function_completion_marker(
                    completion_event_id=completion_event_id,
                    function_name=function_name,
                    tag=tag,
                )
            if first_child == "when":
                dynamic_expr = self.visit(ctx.dynamicExpression())
                action = self._build_invocation_action(
                    function_name=function_name,
                    bindings=bindings,
                    checked=checked,
                    completion_event_id=completion_event_id,
                )
                action.setdefault("metadata", {})
                action["metadata"].setdefault("event_id", event_id)
                action["metadata"].setdefault("dsl_text", self._ctx_text(ctx))
                if tag:
                    action["metadata"].setdefault("invocation_tag", tag)
                self.condition_events.append(
                    {"id": event_id, "dynamic_expr": dynamic_expr, "action": action}
                )
                self._persist_event(
                    event_id=event_id,
                    action=action,
                    time_spec="condition",
                    condition_expr=dynamic_expr,
                )
                return None
            if first_child == "after":
                dependency_label = self.visit(ctx.stringAtom())
                dependency_id = self.labels.get(dependency_label)
                if dependency_id is None:
                    raise ValueError(f"Tag '{dependency_label}' not defined")
                action = self._build_invocation_action(
                    function_name=function_name,
                    bindings=bindings,
                    checked=checked,
                    completion_event_id=completion_event_id,
                )
                action.setdefault("metadata", {})
                action["metadata"].setdefault("event_id", event_id)
                action["metadata"].setdefault("dsl_text", self._ctx_text(ctx))
                if tag:
                    action["metadata"].setdefault("invocation_tag", tag)
                self.dependent_events.append(
                    {"id": event_id, "dependency": dependency_id, "action": action}
                )
                self._persist_event(
                    event_id=event_id,
                    action=action,
                    time_spec="point",
                    dependency_id=dependency_id,
                )
                return None
            invocation_time = self._resolve_now()
            if ctx.timeSpec():
                time_spec = self.visit(ctx.timeSpec())
                if isinstance(time_spec, dict):
                    raise ValueError("Interval-based function invocations are not supported.")
                invocation_time = float(time_spec)
            self._expand_function_invocation(
                function_name=function_name,
                bindings=bindings,
                invocation_time=invocation_time,
                checked=checked,
                completion_event_id=completion_event_id,
            )
            return None

        if tag:
            self.labels[tag] = event_id

        if first_child == "when":
            dynamic_expr = self.visit(ctx.dynamicExpression())
            action = self.visit(executable_ctx.action())
            if isinstance(action, dict):
                action.setdefault("metadata", {})
                action["metadata"].setdefault("event_id", event_id)
                action["metadata"].setdefault("dsl_text", self._ctx_text(ctx))
                if tag:
                    action["metadata"].setdefault("tag", tag)
            self.condition_events.append(
                {"id": event_id, "dynamic_expr": dynamic_expr, "action": action}
            )
            self._persist_event(
                event_id=event_id,
                action=action,
                time_spec="condition",
                condition_expr=dynamic_expr,
                tag=tag,
            )
            return None

        if first_child == "after":
            dependency_label = self.visit(ctx.stringAtom())
            action = self.visit(executable_ctx.action())
            if isinstance(action, dict):
                action.setdefault("metadata", {})
                action["metadata"].setdefault("event_id", event_id)
                action["metadata"].setdefault("dsl_text", self._ctx_text(ctx))
                if tag:
                    action["metadata"].setdefault("tag", tag)
            dependency_id = self.labels.get(dependency_label)
            if dependency_id is None:
                raise ValueError(f"Tag '{dependency_label}' not defined")
            self.dependent_events.append(
                {"id": event_id, "dependency": dependency_id, "action": action}
            )
            self._persist_event(
                event_id=event_id,
                action=action,
                time_spec="point",
                dependency_id=dependency_id,
                tag=tag,
            )
            return None

        time_spec = self.visit(ctx.timeSpec()) if ctx.timeSpec() else self._resolve_now()
        if isinstance(time_spec, dict) and "interval" in time_spec:
            time_spec.setdefault("progress", 0.0)
        action = self.visit(executable_ctx.action())
        if isinstance(action, dict):
            action.setdefault("metadata", {})
            action["metadata"].setdefault("event_id", event_id)
            action["metadata"].setdefault("dsl_text", self._ctx_text(ctx))
            if tag:
                action["metadata"].setdefault("tag", tag)
            if not isinstance(time_spec, dict):
                try:
                    action.setdefault("t_start", float(time_spec))
                except (TypeError, ValueError):
                    pass
        template_action = copy.deepcopy(action)
        self.time_events.append(
            {
                "id": event_id,
                "time_spec": time_spec,
                "action": action,
                "template": template_action,
            }
        )

        if isinstance(time_spec, dict) and "interval" in time_spec:
            start, end = time_spec["interval"]
            self._persist_event(
                event_id=event_id,
                action=action,
                time_spec="interval",
                interval_start=start,
                interval_end=end,
                law=time_spec.get("law"),
                tag=tag,
            )
            return None

        scheduled_at = None
        try:
            scheduled_at = float(time_spec)
        except (TypeError, ValueError):
            scheduled_at = None
        lead = getattr(self, "time_step", None)
        try:
            lead_val = float(lead) if lead is not None else 0.0
        except (TypeError, ValueError):
            lead_val = 0.0
        if lead_val <= 0:
            lead_val = 1e-3
        due_at = max(0.0, scheduled_at - lead_val) if scheduled_at is not None else None
        self._persist_event(
            event_id=event_id,
            action=action,
            time_spec="point",
            at=scheduled_at,
            due_at=due_at,
            tag=tag,
        )
        return None

    def visitTimeSpec(self, ctx):
        if ctx.intervalSpec():
            return self.visit(ctx.intervalSpec())
        return self.visit(ctx.timeExpr())

    def visitIntervalSpec(self, ctx):
        start = self.visit(ctx.timeExpr(0))
        end = self.visit(ctx.timeExpr(1))
        law = "linear"
        if ctx.lawSpec():
            law_text = ctx.lawSpec().getText()
            law = law_text.strip('"')
        return {"interval": (start, end), "law": law}

    def visitRelativeTimeSpec(self, ctx):
        if ctx.relativeIntervalSpec():
            return self.visit(ctx.relativeIntervalSpec())
        return self.visit(ctx.relativeTimeExpr())

    def visitRelativeIntervalSpec(self, ctx):
        start = self.visit(ctx.relativeTimeExpr(0))
        end = self.visit(ctx.relativeTimeExpr(1))
        law = "linear"
        if ctx.lawSpec():
            law_text = ctx.lawSpec().getText()
            law = law_text.strip('"')
        return {"interval": (start, end), "law": law}

    def visitTimeExpr(self, ctx):
        if ctx.timeValue():
            return self.visit(ctx.timeValue())
        if ctx.nowExpr():
            return self.visit(ctx.nowExpr())
        if ctx.IDENTIFIER():
            return float(self._resolve_identifier_value(ctx.IDENTIFIER().getText()))
        return None

    def visitRelativeTimeExpr(self, ctx):
        if ctx.relativeTimeValue():
            return self.visit(ctx.relativeTimeValue())
        if ctx.IDENTIFIER():
            return float(self._resolve_identifier_value(ctx.IDENTIFIER().getText()))
        return None

    def visitNowExpr(self, ctx):
        base_time = self._resolve_now()
        if ctx.timeValue() is None:
            return base_time
        offset = self.visit(ctx.timeValue())
        sign_token = ctx.getChild(1).getText()
        if sign_token == "-":
            offset = -offset
        return base_time + offset

    def visitTimeValue(self, ctx):
        time_value = self.visit(ctx.numericAtom())
        time_unit = ctx.timeUnit().getText()
        return to_seconds(time_value, time_unit)

    def visitRelativeTimeValue(self, ctx):
        time_value = self.visit(ctx.signedNumericAtom())
        time_unit = ctx.timeUnit().getText()
        return to_seconds(time_value, time_unit)
