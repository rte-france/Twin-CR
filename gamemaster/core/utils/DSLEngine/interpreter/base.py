"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Foundational classes shared by concrete power-event DSL interpreters.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..antlr.PowerEventDSLVisitor import PowerEventDSLVisitor

logger = logging.getLogger(__name__)


class BaseDSLInterpreter(PowerEventDSLVisitor):
    """Shared interpreter state and persistence helpers.

    Parameters
    ----------
    artifact_id : str
        IIDM artefact identifier used when resolving dynamic targets.
    event_store : object, optional
        Persistence backend used to enqueue and update DSL-driven events.
    simulation_name : str, optional
        Name associated with the current simulation run. Used in persistence
        identifiers.
    event_source : str, default="dsl"
        Descriptive source tag stored alongside persisted events.

    Attributes
    ----------
    time_events : list[dict]
        Scheduled time-based events produced while walking the DSL.
    condition_events : list[dict]
        Events that depend on dynamic expressions evaluated during runtime.
    dependent_events : list[dict]
        Events gated by other event completions.
    completed_events : set[str]
        Identifiers of events already emitted.
    new_measurement_keys : set[str]
        Measurement identifiers inferred during interpretation for subscription
        purposes.
    """

    def __init__(
        self,
        artifact_id,
        event_store=None,
        simulation_name: Optional[str] = None,
        event_source: str = "dsl",
    ):
        super().__init__()
        self.artifact_id = artifact_id
        self.duration = None
        self.time_step = None
        self.time_events = []
        self.condition_events = []
        self.dependent_events = []
        self.current_time = 0.0
        self.completed_events = set()
        self.labels = {}
        self.iidm_cache = {}  # In-memory cache for IIDM properties
        self.event_store = event_store  # Optional persistent store
        self.simulation_name = simulation_name
        self.event_source = event_source
        self.new_measurement_keys: set[str] = set()
        logger.debug("DSLInterpreter initialized with artifact_id: %s", artifact_id)

    def _epsilon(self) -> float:
        """Return a small epsilon derived from the configured time step.

        Returns
        -------
        float
            A small positive number that scales with ``time_step`` when
            available, or ``1e-3`` as a fallback.
        """
        try:
            ts = float(self.time_step or 0.0)
        except Exception:
            ts = 0.0
        return max(1e-3, ts / 10.0) if ts > 0 else 1e-3

    def _persist_event(
        self,
        *,
        event_id: str,
        source: Optional[str] = None,
        action: dict,
        time_spec: str,
        at: float = None,
        interval_start: float = None,
        interval_end: float = None,
        law: str = None,
        condition_expr=None,
        dependency_id: str = None,
        due_at: float = None,
        tag: str = None,
    ):
        """Forward an interpreted event to the persistence backend.

        Parameters
        ----------
        event_id : str
            Unique identifier attached to the interpreted event.
        source : str, optional
            Source label overriding the instance-level ``event_source``.
        action : dict
            Event payload describing the target operation.
        time_spec : str
            Time classification (``"point"``, ``"interval"`` or ``"condition"``).
        at : float, optional
            Absolute timestamp for ``"point"`` events.
        interval_start, interval_end : float, optional
            Interval boundaries for continuous events.
        law : str, optional
            Progression law applied during intervals.
        condition_expr : Any
            Expression attached to condition-driven events.
        dependency_id : str, optional
            Identifier of the predecessor event when modelling dependencies.
        """
        if self.event_store is None:
            return
        try:
            computed_due_at = None
            if due_at is None:
                lead = self.time_step if self.time_step is not None else self._epsilon()
                try:
                    lead_val = float(lead)
                except (TypeError, ValueError):
                    lead_val = self._epsilon()
                if time_spec == "point" and at is not None:
                    computed_due_at = max(0.0, float(at) - max(lead_val, 0.0))
                elif time_spec == "interval" and interval_start is not None:
                    computed_due_at = max(0.0, float(interval_start) - max(lead_val, 0.0))
            elif due_at is not None:
                try:
                    computed_due_at = float(due_at)
                except (TypeError, ValueError):
                    computed_due_at = None
            source = source or self.event_source
            evt_type = action.get("type", "unknown")
            target = action.get("id") if "id" in action else action.get("target")
            payload = self._build_action_payload(action)
            metadata = action.get("metadata") if isinstance(action, dict) else None

            def _normalize_target(t):
                if isinstance(t, list):
                    try:
                        return ",".join(sorted(map(str, t)))
                    except Exception:
                        return ",".join(map(str, t))
                return str(t)

            # Build idempotency key to avoid duplicates across re-inits
            idemp = (
                f"dsl:{self.simulation_name}:{evt_type}:{_normalize_target(target)}:"
                f"{at or interval_start}:{interval_end or ''}:{law or ''}:"
                f"{dependency_id or ''}:{tag or ''}"
            )
            # Dependent events without explicit time stay pending until promoted
            status_override = None
            if time_spec == "point" and dependency_id and not at:
                status_override = "pending"
            self.event_store.enqueue_event(
                source=source,
                type=evt_type,
                target=target,
                payload=payload or None,
                metadata=metadata,
                time_spec=time_spec,
                at=at,
                interval_start=interval_start,
                interval_end=interval_end,
                law=law,
                condition_expr=condition_expr,
                dependency_id=dependency_id,
                event_id=event_id,
                idempotency_key=idemp,
                simulation=self.simulation_name,
                status=status_override,
                due_at=computed_due_at,
                tag=tag,
            )
        except Exception as e:
            logger.warning("Failed to persist DSL event %s: %s", event_id, e)


__all__ = ["BaseDSLInterpreter"]
