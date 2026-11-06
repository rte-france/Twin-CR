"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Interpretation logic for event declarations in the power-event DSL.
"""

from __future__ import annotations

import copy
import logging
import uuid

from .time_config import TimeConfigurationInterpreter
from antlr4 import ParserRuleContext

logger = logging.getLogger(__name__)


class EventDefinitionInterpreter(TimeConfigurationInterpreter):
    """Manage event definitions and persistence bookkeeping."""

    @staticmethod
    def _ctx_text(ctx: ParserRuleContext) -> str:
        """Return the original DSL slice for this context, preserving spaces when possible."""
        try:
            stream = ctx.start.getInputStream()
            if stream:
                return stream.getText(ctx.start.start, ctx.stop.stop)
        except Exception:
            pass
        return ctx.getText()

    def visitEventDef(self, ctx):
        """Interpret an ``event`` statement and register its metadata.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for the ``eventDef`` rule.

        Raises
        ------
        ValueError
            If a dependent event references an unknown label.
        """
        event_id = str(uuid.uuid4())
        tag = None
        if ctx.tagged():
            tag = ctx.tagged().STRING().getText()[1:-1]
            self.labels[tag] = event_id

        first_child = ctx.getChild(0).getText()
        if first_child == "when":
            dynamic_expr = self.visit(ctx.dynamicExpression())
            action = self.visit(ctx.action())
            if isinstance(action, dict):
                action.setdefault("metadata", {})
                action["metadata"].setdefault("event_id", event_id)
                action["metadata"].setdefault("dsl_text", self._ctx_text(ctx))
                if tag:
                    action["metadata"].setdefault("tag", tag)
            self.condition_events.append(
                {"id": event_id, "dynamic_expr": dynamic_expr, "action": action}
            )
            logger.debug(
                "Added condition-based event: %s",
                {"id": event_id, "dynamic_expr": dynamic_expr, "action": action},
            )
            self._persist_event(
                event_id=event_id,
                action=action,
                time_spec="condition",
                condition_expr=dynamic_expr,
                tag=tag,
            )
        elif first_child == "after":
            dependency_label = ctx.STRING().getText()[1:-1]
            action = self.visit(ctx.action())
            if isinstance(action, dict):
                action.setdefault("metadata", {})
                action["metadata"].setdefault("event_id", event_id)
                action["metadata"].setdefault("dsl_text", self._ctx_text(ctx))
                if tag:
                    action["metadata"].setdefault("tag", tag)
            dependency_id = self.labels.get(dependency_label)
            if dependency_id is None:
                logger.error("Undefined tag '%s' in dependent event", dependency_label)
                raise ValueError(f"Tag '{dependency_label}' not defined")
            self.dependent_events.append(
                {"id": event_id, "dependency": dependency_id, "action": action}
            )
            logger.debug(
                "Added dependent event: %s",
                {"id": event_id, "dependency": dependency_id, "action": action},
            )
            self._persist_event(
                event_id=event_id,
                action=action,
                time_spec="point",
                dependency_id=dependency_id,
                tag=tag,
            )
        else:
            time_spec = (
                self.visit(ctx.timeSpec()) if ctx.timeSpec() else self._resolve_now()
            )
            if isinstance(time_spec, dict) and "interval" in time_spec:
                time_spec.setdefault("progress", 0.0)
            action = self.visit(ctx.action())
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
            logger.debug(
                "Added time-based event: %s",
                {"id": event_id, "time_spec": time_spec, "action": action},
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
            else:
                lead = self.time_step if self.time_step is not None else self._epsilon()
                try:
                    lead_val = float(lead)
                except (TypeError, ValueError):
                    lead_val = self._epsilon()
                scheduled_at = None
                try:
                    scheduled_at = float(time_spec)
                except (TypeError, ValueError):
                    scheduled_at = None
                due_at = (
                    max(0.0, scheduled_at - max(lead_val, 0.0))
                    if scheduled_at is not None
                    else None
                )
                self._persist_event(
                    event_id=event_id,
                    action=action,
                    time_spec="point",
                    at=scheduled_at,
                    due_at=due_at,
                    tag=tag,
                )


__all__ = ["EventDefinitionInterpreter"]
