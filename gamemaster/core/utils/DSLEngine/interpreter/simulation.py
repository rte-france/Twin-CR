"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Simulation loop helpers layered on top of the expression interpreter.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, timedelta
from typing import Optional

from .expressions import ExpressionInterpreter

logger = logging.getLogger(__name__)


class SimulationInterpreter(ExpressionInterpreter):
    """Run the simulation timeline and expose status helpers."""

    def start_simulation(self):
        """Initialise timeline state and sort time-based events.

        Raises
        ------
        ValueError
            If duration or time step were not defined in the DSL program.
        """
        if self.duration is None or self.time_step is None:
            raise ValueError("Simulation duration or time step not set")
        self.current_time = 0.0
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=self.duration)

        def event_sort_key(event):
            ts = event["time_spec"]
            return (
                ts["interval"][0] if isinstance(ts, dict) and "interval" in ts else ts
            )

        self.time_events.sort(key=event_sort_key)
        logger.info(
            "Simulation started: duration=%s sec, time_step=%s sec",
            self.duration,
            self.time_step,
        )

    def get_current_step_actions(self, new_time: float, system_state=None):
        """Advance the simulation to ``new_time`` and compute emitted actions.

        Parameters
        ----------
        new_time : float
            Target simulation time in seconds.
        system_state : dict, optional
            Measurement data used when preparing actions.

        Returns
        -------
        dict
            Dictionary describing the current time, emitted actions and status
            flag.

        Raises
        ------
        ValueError
            If ``new_time`` precedes the current time.
        """
        if system_state is None:
            system_state = {}
        if new_time < self.current_time:
            logger.error(
                "New time %s is less than current simulation time %s",
                new_time,
                self.current_time,
            )
            raise ValueError("New time must be >= current simulation time")
        if new_time > self.duration:
            logger.debug(
                "New time %s exceeds duration %s, setting to duration",
                new_time,
                self.duration,
            )
            new_time = self.duration

        self.current_time = new_time
        logger.debug("Current simulation time updated to %s", self.current_time)

        current_actions = []
        newly_completed = set()

        eps = self._epsilon()
        # Process time-based events
        for event in self.time_events:
            ts = event["time_spec"]
            if isinstance(ts, dict) and "interval" in ts:
                start, end = ts["interval"]
                if start <= self.current_time <= end:
                    action_copy = copy.deepcopy(event["action"])
                    law = ts.get("law")
                    base_template = (
                        event.get("template") if isinstance(event, dict) else None
                    )
                    if base_template is None:
                        base_template = event["action"]
                    self._apply_interval_law(
                        action_copy, base_template, law, start, end
                    )
                    current_actions.append(
                        {
                            "action": action_copy,
                            "law": law,
                            "interval_start": start,
                            "interval_end": end,
                        }
                    )
                    if self.current_time == end:
                        newly_completed.add(event["id"])
            elif abs(ts - self.current_time) < eps:
                current_actions.append(event["action"])
                newly_completed.add(event["id"])

        # Process condition-based events
        for event in self.condition_events:
            if self.evaluate_dynamic_expression(event["dynamic_expr"], system_state):
                current_actions.append(event["action"])
                newly_completed.add(event["id"])

        updated_dependent_events = []
        step_delay = self.time_step if self.time_step else self._epsilon()
        # Process dependent events (trigger in the first step after dependency completion)
        for event in self.dependent_events:
            ready_at = event.get("ready_at")
            dependency_id = event["dependency"]
            if ready_at is not None:
                if self.current_time + self._epsilon() >= ready_at:
                    current_actions.append(event["action"])
                    newly_completed.add(event["id"])
                else:
                    updated_dependent_events.append(event)
                continue

            if dependency_id in newly_completed:
                event["ready_at"] = self.current_time + step_delay
                updated_dependent_events.append(event)
            elif dependency_id in self.completed_events:
                current_actions.append(event["action"])
                newly_completed.add(event["id"])
            else:
                updated_dependent_events.append(event)

        # Update completed events and keep pending dependent events
        self.completed_events.update(newly_completed)
        self.dependent_events = updated_dependent_events

        enriched_actions = []
        for action in current_actions:
            if isinstance(action, dict) and "action" in action:
                prepared = self.prepare_action(action["action"], system_state)
                action["action"] = prepared
                enriched_actions.append(action)
            else:
                enriched_actions.append(self.prepare_action(action, system_state))

        if self.event_store is not None:
            for item in enriched_actions:
                candidate = (
                    item["action"]
                    if isinstance(item, dict) and "action" in item
                    else item
                )
                if not isinstance(candidate, dict):
                    continue
                metadata = candidate.get("metadata") or {}
                event_id = metadata.get("event_id")
                if not event_id:
                    continue
                payload = self._build_action_payload(candidate)
                try:
                    self.event_store.update_payload(event_id, payload or None)
                except Exception as exc:  # pragma: no cover
                    logger.debug(
                        "Failed to update payload for event %s: %s", event_id, exc
                    )

        step_data = {
            "current_time": self.current_time,
            "actions": enriched_actions,
            "status": (
                "running" if self.current_time < self.duration else "simulation_ended"
            ),
        }
        logger.debug("Step data: %s", step_data)
        return step_data

    def _apply_interval_law(
        self,
        action: dict,
        base_action: dict,
        law: Optional[str],
        start: Optional[float],
        end: Optional[float],
    ) -> bool:
        """Scale an action across a time interval according to its law.

        Parameters
        ----------
        action : dict
            Action instance to mutate.
        base_action : dict
            Template action capturing the total delta over the interval.
        law : str, optional
            Interpolation law (currently supports ``"linear"``).
        start, end : float, optional
            Interval boundaries in seconds.

        Returns
        -------
        bool
            ``True`` when there are remaining increments after this step.
        """
        if not isinstance(action, dict):
            return True
        if not law:
            return True
        law_normalized = str(law).strip().lower()
        if law_normalized != "linear":
            return True
        if start is None or end is None or end <= start:
            return False

        span = end - start
        if span <= 0:
            return False
        total_percent = None
        if isinstance(base_action, dict):
            total_percent = base_action.get("percentage")
            if total_percent is None:
                total_percent = base_action.get("setpoint", {}).get("delta_percent")
        if total_percent is None:
            return True
        try:
            total_percent = float(total_percent)
        except (TypeError, ValueError):
            return True

        step_seconds = self.time_step if self.time_step and self.time_step > 0 else span
        steps = max(1, int(round(span / step_seconds)))
        step_increment = total_percent / float(steps)

        elapsed = self.current_time - start
        if elapsed < 0:
            applied_steps = 0
        else:
            applied_steps = min(steps, int(round(elapsed / step_seconds)))

        current_percent = step_increment * applied_steps

        action["percentage"] = current_percent
        if isinstance(action.get("setpoint"), dict):
            action["setpoint"]["delta_percent"] = current_percent

        return applied_steps < steps

    @staticmethod
    def _scale_action_for_fraction(
        action: dict, base_action: dict, fraction: float
    ) -> None:
        """Scale a multi-target action by the given fractional progress.

        Parameters
        ----------
        action : dict
            Action instance to mutate.
        base_action : dict
            Template action containing the original deltas.
        fraction : float
            Fraction between ``0`` and ``1`` describing the applied progress.
        """
        try:
            frac = float(fraction)
        except (TypeError, ValueError):
            return
        frac = max(0.0, min(1.0, frac))

        base_percentage = None
        if isinstance(base_action, dict):
            base_percentage = base_action.get("percentage")
            if base_percentage is None:
                base_percentage = base_action.get("setpoint", {}).get("delta_percent")
        if base_percentage is not None:
            try:
                scaled = float(base_percentage) * frac
            except (TypeError, ValueError):
                scaled = None
            if scaled is not None:
                action["percentage"] = scaled
                if isinstance(action.get("setpoint"), dict):
                    action["setpoint"]["delta_percent"] = scaled

        action_setpoints = action.get("setpoints") if isinstance(action, dict) else None
        base_setpoints = (
            base_action.get("setpoints") if isinstance(base_action, dict) else None
        )
        if isinstance(action_setpoints, list) and isinstance(base_setpoints, list):
            for entry, base_entry in zip(action_setpoints, base_setpoints):
                if not isinstance(entry, dict) or not isinstance(base_entry, dict):
                    continue
                delta = base_entry.get("delta_percent")
                try:
                    scaled_delta = float(delta) * frac
                except (TypeError, ValueError):
                    continue
                entry["delta_percent"] = scaled_delta

    def get_current_status(self, system_state=None):
        """Return the current simulation status without advancing time.

        Parameters
        ----------
        system_state : dict, optional
            Measurement data used to re-evaluate condition events.

        Returns
        -------
        dict
            Summary of the current simulation time, active actions, and status
            flag.
        """
        if system_state is None:
            system_state = {}
        current_actions = []
        # Include actions from the current step
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


class DSLInterpreter(SimulationInterpreter):
    """Facade combining the specialised interpreter stages into the public API."""


__all__ = ["SimulationInterpreter", "DSLInterpreter"]
