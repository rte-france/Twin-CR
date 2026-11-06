"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Helpers that turn DSL action statements into runtime payload structures.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..common import to_seconds
from .targets import TargetResolutionInterpreter

logger = logging.getLogger(__name__)


class ActionInterpreter(TargetResolutionInterpreter):
    """Build action payloads and measurement metadata."""

    def visitSwitchAction(self, ctx):
        """Interpret a switch operation statement.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``switchAction``.

        Returns
        -------
        dict
            Minimal action dictionary representing the switch operation.
        """
        operation = ctx.getChild(0).getText()
        switch_id = ctx.STRING().getText()[1:-1]
        action = {"type": f"{operation}_switch", "id": switch_id}
        logger.debug("Parsed switch action: %s", action)
        return action

    def visitLineAction(self, ctx):
        """Interpret a line operation statement."""
        operation = ctx.getChild(0).getText()
        line_id = ctx.STRING().getText()[1:-1]
        action = {"type": f"{operation}_line", "id": line_id}
        logger.debug("Parsed line action: %s", action)
        return action

    def visitLoadAction(self, ctx):
        """Interpret a load adjustment statement.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``loadAction``.

        Returns
        -------
        dict
            Action metadata ready to be further prepared for execution.
        """
        operation = ctx.getChild(0).getText()
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        percentage = float(ctx.NUMBER().getText())
        attribute = self._parse_channel(ctx.channelSpec())

        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            self._measurement_key("load", attribute, tid) for tid in target_ids if tid
        ]
        action = {
            "type": f"{operation}_load",
            "target": simplified_target,
            "targets": target_ids,
            "percentage": percentage,
            "attribute": attribute,
            "element_type": "load",
            "operation": operation,
            "setpoint": {
                "attribute": attribute,
                "delta_percent": percentage,
            },
        }
        action["target_percentage"] = percentage
        if isinstance(target_spec, dict) and target_spec:
            action["target_spec"] = target_spec
        if measurement_keys:
            self.new_measurement_keys.update(measurement_keys)
            action["measurement_keys"] = measurement_keys
        logger.debug("Parsed load action: %s", action)
        return action

    def visitGenAction(self, ctx):
        """Interpret a generator adjustment statement.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``genAction``.

        Returns
        -------
        dict
            Action metadata ready to be further prepared for execution.
        """
        operation = ctx.getChild(0).getText()
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        percentage = float(ctx.NUMBER().getText())
        attribute = self._parse_channel(ctx.channelSpec())

        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            self._measurement_key("generator", attribute, tid)
            for tid in target_ids
            if tid
        ]
        action = {
            "type": f"{operation}_generator",
            "target": simplified_target,
            "targets": target_ids,
            "percentage": percentage,
            "attribute": attribute,
            "element_type": "generator",
            "operation": operation,
            "setpoint": {
                "attribute": attribute,
                "delta_percent": percentage,
            },
        }
        action["target_percentage"] = percentage
        if isinstance(target_spec, dict) and target_spec:
            action["target_spec"] = target_spec
        if measurement_keys:
            self.new_measurement_keys.update(measurement_keys)
            action["measurement_keys"] = measurement_keys
        logger.debug("Parsed generator action: %s", action)
        return action

    def visitSetLoadAction(self, ctx):
        """Interpret a load absolute setpoint statement."""
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        range_ctx = ctx.setRange()
        numbers = range_ctx.signedNumber()
        absolute_value = float(numbers[-1].getText())
        from_value = float(numbers[0].getText()) if len(numbers) > 1 else None
        attribute = self._parse_channel(ctx.channelSpec())

        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            self._measurement_key("load", attribute, tid) for tid in target_ids if tid
        ]
        action = {
            "type": "set_load",
            "target": simplified_target,
            "targets": target_ids,
            "value": absolute_value,
            "attribute": attribute,
            "element_type": "load",
            "operation": "set",
            "setpoint": {"attribute": attribute, "absolute_value": absolute_value},
        }
        if from_value is not None:
            action["setpoint"]["from_value"] = from_value
        if isinstance(target_spec, dict) and target_spec:
            action["target_spec"] = target_spec
        if measurement_keys:
            self.new_measurement_keys.update(measurement_keys)
            action["measurement_keys"] = measurement_keys
        logger.debug("Parsed set load action: %s", action)
        return action

    def visitSetGenAction(self, ctx):
        """Interpret a generator absolute setpoint statement."""
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        range_ctx = ctx.setRange()
        numbers = range_ctx.signedNumber()
        absolute_value = float(numbers[-1].getText())
        from_value = float(numbers[0].getText()) if len(numbers) > 1 else None
        attribute = self._parse_channel(ctx.channelSpec())

        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            self._measurement_key("generator", attribute, tid)
            for tid in target_ids
            if tid
        ]
        action = {
            "type": "set_generator",
            "target": simplified_target,
            "targets": target_ids,
            "value": absolute_value,
            "attribute": attribute,
            "element_type": "generator",
            "operation": "set",
            "setpoint": {"attribute": attribute, "absolute_value": absolute_value},
        }
        if from_value is not None:
            action["setpoint"]["from_value"] = from_value
        if isinstance(target_spec, dict) and target_spec:
            action["target_spec"] = target_spec
        if measurement_keys:
            self.new_measurement_keys.update(measurement_keys)
            action["measurement_keys"] = measurement_keys
        logger.debug("Parsed set generator action: %s", action)
        return action

    def visitFaultAction(self, ctx):
        """Interpret a fault application statement.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``faultAction``.

        Returns
        -------
        dict
            Action dictionary describing the fault to apply.
        """
        component_type = ctx.component().componentType().getText()
        component_id = ctx.component().STRING().getText()[1:-1]
        action = {
            "type": "apply_fault",
            "component_type": component_type,
            "id": component_id,
        }
        logger.debug("Parsed fault action: %s", action)
        return action

    def visitClearFaultAction(self, ctx):
        """Interpret a fault clearance statement.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``clearFaultAction``.

        Returns
        -------
        dict
            Action dictionary describing the fault to clear.
        """
        component_type = ctx.component().componentType().getText()
        component_id = ctx.component().STRING().getText()[1:-1]
        action = {
            "type": "clear_fault",
            "component_type": component_type,
            "id": component_id,
        }
        logger.debug("Parsed clear fault action: %s", action)
        return action

    def visitNetworkAction(self, ctx):
        action: Dict[str, Any] = {
            "type": "change_network_characteristics",
            "links": [],
            "nodes": [],
        }
        delay_func: Optional[Dict[str, Any]] = None
        drop_func: Optional[Dict[str, Any]] = None
        corruption_funcs: List[Dict[str, Any]] = []

        # Collect links and/or nodes
        if ctx.linkStatement():
            link_stmt = ctx.linkStatement()
            for lc in link_stmt.linkClause():
                action["links"].append(self.visit(lc))
            if ctx.nodeStatement():
                node_stmt = ctx.nodeStatement()
                for nc in node_stmt.nodeClause():
                    action["nodes"].append(self.visit(nc))
        elif ctx.nodeStatement():
            node_stmt = ctx.nodeStatement()
            for nc in node_stmt.nodeClause():
                action["nodes"].append(self.visit(nc))

        # Collect adjustments
        for adj in ctx.networkAdjustmentClause() or []:
            if adj.delayClause():
                if delay_func is not None:
                    raise ValueError(
                        "Delay function specified more than once in network change."
                    )
                delay_func = self.visit(adj.delayClause())
            elif adj.dropClause():
                if drop_func is not None:
                    raise ValueError(
                        "Drop function specified more than once in network change."
                    )
                drop_func = self.visit(adj.dropClause())
            elif adj.corruptionClause():
                corruption_funcs.append(self.visit(adj.corruptionClause()))

        if not action["links"] and not action["nodes"]:
            raise ValueError(
                "Network change requires at least one link or node clause."
            )

        if delay_func is not None:
            action["delay_function"] = delay_func
        if drop_func is not None:
            action["drop_function"] = drop_func
        if corruption_funcs:
            action["corruption_functions"] = corruption_funcs

        logger.debug("Parsed network action: %s", action)
        return action

    def visitNetworkClause(self, ctx):
        if ctx.linkClause():
            return "link", self.visit(ctx.linkClause())
        if ctx.nodeClause():
            return "node", self.visit(ctx.nodeClause())
        if ctx.delayClause():
            return "delay", self.visit(ctx.delayClause())
        if ctx.dropClause():
            return "drop", self.visit(ctx.dropClause())
        if ctx.corruptionClause():
            return "corruption", self.visit(ctx.corruptionClause())
        raise ValueError("Unsupported network clause.")

    def visitLinkClause(self, ctx):
        src = self._strip_quotes(ctx.STRING(0).getText())
        dst = self._strip_quotes(ctx.STRING(1).getText())
        return {"from": src, "to": dst}

    def visitNodeClause(self, ctx):
        return self._strip_quotes(ctx.STRING().getText())

    def visitDelayClause(self, ctx):
        return self.visit(ctx.delayFunction())

    def visitDelayFunction(self, ctx):
        head = ctx.getChild(0).getText()
        if head == "fixed":
            value = float(ctx.NUMBER(0).getText())
            unit = ctx.timeUnit(0).getText() if ctx.timeUnit() else None
            return {
                "type": "fixed",
                "delay": self._convert_to_seconds(value, unit),
            }
        if head == "gauss":
            mean_val = float(ctx.NUMBER(0).getText())
            std_val = float(ctx.NUMBER(1).getText())
            units = ctx.timeUnit()
            mean_unit = units[0].getText() if len(units) > 0 else None
            std_unit = units[1].getText() if len(units) > 1 else None
            return {
                "type": "gauss",
                "mean": self._convert_to_seconds(mean_val, mean_unit),
                "stddev": self._convert_to_seconds(std_val, std_unit),
            }
        raise ValueError("Unknown delay function type.")

    def visitDropClause(self, ctx):
        return self.visit(ctx.dropFunction())

    def visitDropFunction(self, ctx):
        head = ctx.getChild(0).getText()
        if head == "fixed":
            literal = ctx.booleanLiteral().getText().lower()
            value = literal == "true"
            return {"type": "fixed", "value": value}
        if head == "random":
            probability = float(ctx.NUMBER().getText())
            return {"type": "random", "value": probability}
        raise ValueError("Unknown drop function type.")

    def visitCorruptionClause(self, ctx):
        return self.visit(ctx.corruptionFunction())

    def visitCorruptionFunction(self, ctx):
        head = ctx.getChild(0).getText()
        if head == "none":
            likelihood = 1.0
            if ctx.NUMBER():
                likelihood = float(ctx.NUMBER().getText())
            return {"type": "NoCorruption", "likelihood": likelihood}
        if head == "random_noise_measurement":
            params = self.visit(ctx.corruptionNoiseParams())
            result = {
                "type": "RandomNoiseMeasurementCorruption",
                "noise_min": params["noise_min"],
                "noise_max": params["noise_max"],
            }
            if params.get("likelihood") is not None:
                result["likelihood"] = params["likelihood"]
            return result
        if head == "random_noise_control":
            params = self.visit(ctx.corruptionNoiseParams())
            result = {
                "type": "RandomNoiseControlCorruption",
                "noise_min": params["noise_min"],
                "noise_max": params["noise_max"],
            }
            if params.get("likelihood") is not None:
                result["likelihood"] = params["likelihood"]
            return result
        if head == "zero_out_measurement":
            params = self.visit(ctx.corruptionZeroParams())
            result = {"type": "ZeroOutMeasurementCorruption"}
            if params.get("likelihood") is not None:
                result["likelihood"] = params["likelihood"]
            if params.get("zero_value") is not None:
                result["zero_value"] = params["zero_value"]
            return result
        if head == "shift_measurement":
            params = self.visit(ctx.corruptionShiftParams())
            result = {
                "type": "ShiftMeasurementCorruption",
                "shift_value": params["shift_value"],
            }
            if params.get("likelihood") is not None:
                result["likelihood"] = params["likelihood"]
            return result
        if head == "invert_control":
            params = self.visit(ctx.corruptionInvertParams())
            result = {"type": "InvertControlCorruption"}
            if params.get("invert_factor") is not None:
                result["invert_factor"] = params["invert_factor"]
            if params.get("likelihood") is not None:
                result["likelihood"] = params["likelihood"]
            return result
        raise ValueError("Unknown corruption function type.")

    def visitCorruptionNoiseParams(self, ctx):
        likelihood = None
        noise_min = None
        noise_max = None
        children = list(ctx.getChildren() or [])
        idx = 0
        while idx < len(children):
            token = children[idx].getText()
            if token == "likelihood":
                likelihood = float(children[idx + 1].getText())
                idx += 2
            elif token == "range":
                noise_min = float(children[idx + 1].getText())
                if children[idx + 2].getText() != "to":
                    raise ValueError('Noise range must use "to" delimiter.')
                noise_max = float(children[idx + 3].getText())
                idx += 4
            else:
                idx += 1
        if noise_min is None or noise_max is None:
            raise ValueError("Random noise corruption requires a range.")
        return {
            "likelihood": likelihood,
            "noise_min": noise_min,
            "noise_max": noise_max,
        }

    def visitCorruptionZeroParams(self, ctx):
        likelihood = None
        zero_value = None
        children = list(ctx.getChildren() or [])
        idx = 0
        while idx < len(children):
            token = children[idx].getText()
            if token == "likelihood":
                likelihood = float(children[idx + 1].getText())
                idx += 2
            elif token == "value":
                zero_value = float(children[idx + 1].getText())
                idx += 2
            else:
                idx += 1
        return {"likelihood": likelihood, "zero_value": zero_value}

    def visitCorruptionShiftParams(self, ctx):
        likelihood = None
        shift_value = None
        children = list(ctx.getChildren() or [])
        idx = 0
        while idx < len(children):
            token = children[idx].getText()
            if token == "likelihood":
                likelihood = float(children[idx + 1].getText())
                idx += 2
            elif token == "by":
                shift_value = float(children[idx + 1].getText())
                idx += 2
            else:
                idx += 1
        if shift_value is None:
            raise ValueError("Shift corruption must specify value after 'by'.")
        return {"likelihood": likelihood, "shift_value": shift_value}

    def visitCorruptionInvertParams(self, ctx):
        likelihood = None
        invert_factor = None
        children = list(ctx.getChildren() or [])
        idx = 0
        while idx < len(children):
            token = children[idx].getText()
            if token == "likelihood":
                likelihood = float(children[idx + 1].getText())
                idx += 2
            elif token == "by":
                invert_factor = float(children[idx + 1].getText())
                idx += 2
            else:
                idx += 1
        return {"likelihood": likelihood, "invert_factor": invert_factor}

    @staticmethod
    def _strip_quotes(raw: str) -> str:
        if raw.startswith('"') and raw.endswith('"'):
            return raw[1:-1]
        if raw.startswith("'") and raw.endswith("'"):
            return raw[1:-1]
        return raw

    @staticmethod
    def _convert_to_seconds(value: float, unit: Optional[str]) -> float:
        if unit is None:
            return float(value)
        try:
            return float(to_seconds(value, unit))
        except Exception:
            return float(value)

    @staticmethod
    def _normalize_attribute_value(attribute: Optional[str]) -> str:
        attr = attribute or "P"
        attr = str(attr).strip()
        if attr.upper() in {"P", "Q"}:
            return attr.upper()
        if attr.lower() == "state":
            return "state"
        return attr

    @classmethod
    def _parse_channel(cls, channel_ctx):
        """Normalise the attribute token associated with an action channel.

        Parameters
        ----------
        channel_ctx : antlr4.ParserRuleContext or None
            Parse tree node describing the selected attribute.

        Returns
        -------
        str
            Attribute token, defaulting to ``"P"`` when unspecified.
        """
        if channel_ctx is None:
            return "P"
        token = channel_ctx.getText()
        return cls._normalize_attribute_value(token)

    def _build_action_payload(self, action: dict) -> Dict[str, Any]:
        """Extract a lightweight payload for persistence purposes.

        Parameters
        ----------
        action : dict
            Normalised action dictionary produced during interpretation.

        Returns
        -------
        dict
            Compact payload containing only serialisable fields of interest.
        """
        if not isinstance(action, dict):
            return {}

        if str(action.get("type", "")).lower() == "change_network_characteristics":
            payload: Dict[str, Any] = {
                "links": action.get("links") or [],
                "nodes": action.get("nodes") or [],
            }
            if action.get("delay_function") is not None:
                payload["delay_function"] = action.get("delay_function")
            if action.get("drop_function") is not None:
                payload["drop_function"] = action.get("drop_function")
            if action.get("corruption_functions") is not None:
                payload["corruption_functions"] = action.get("corruption_functions")
            if action.get("t_start_from_now") is not None:
                payload["t_start_from_now"] = action.get("t_start_from_now")
            if action.get("t_start") is not None:
                payload["t_start"] = action.get("t_start")
            if action.get("metadata") is not None:
                payload["metadata"] = action.get("metadata")
            return payload

        payload: Dict[str, Any] = {}

        def _maybe_set(key: str, value):
            if value is None:
                return
            if isinstance(value, list) and not value:
                return
            payload[key] = value

        try:
            if "percentage" in action:
                _maybe_set("percentage", float(action["percentage"]))
        except (TypeError, ValueError):
            pass

        try:
            if "target_percentage" in action:
                _maybe_set("target_percentage", float(action["target_percentage"]))
        except (TypeError, ValueError):
            pass

        _maybe_set("attribute", action.get("attribute"))
        _maybe_set("operation", action.get("operation"))
        _maybe_set("element_type", action.get("element_type"))
        _maybe_set("targets", action.get("targets"))
        _maybe_set("measurement_keys", action.get("measurement_keys"))
        _maybe_set("setpoint", action.get("setpoint"))
        _maybe_set("setpoints", action.get("setpoints"))
        _maybe_set("target_spec", action.get("target_spec"))
        return payload

    @classmethod
    def _normalize_attribute_token(cls, attribute: Optional[str]) -> str:
        attr = cls._normalize_attribute_value(attribute)
        if attr == "P":
            return "power_active"
        if attr == "Q":
            return "power_reactive"
        return str(attr).lower()

    @classmethod
    def _measurement_key(
        cls, element_type: str, attribute: str, target_id: str
    ) -> Optional[str]:
        """Compose a measurement key for an element/attribute pair.

        Parameters
        ----------
        element_type : str
            Normalised element category (e.g. ``"load"``).
        attribute : str
            Attribute token (e.g. ``"P"``).
        target_id : str
            Identifier of the target element.

        Returns
        -------
        str or None
            Measurement key suitable for lookup, or ``None`` when insufficient
            information is available.
        """
        if not target_id:
            return None
        element = (element_type or "").strip().lower()
        if not element:
            return None
        attr_token = cls._normalize_attribute_token(attribute)
        return f"{attr_token}:{element}:{str(target_id).strip()}"

    @staticmethod
    def _lookup_measurement(system_state, key: Optional[str]) -> Optional[float]:
        """Fetch the latest measurement value for the given key.

        Parameters
        ----------
        system_state : dict or None
            Mapping of measurement keys to values available at runtime.
        key : str, optional
            Measurement identifier generated by :meth:`_measurement_key`.

        Returns
        -------
        float or None
            Numeric measurement value if present and convertible, otherwise
            ``None``.
        """
        if not key or not system_state:
            return None
        value = system_state.get(key)
        if value is None:
            value = system_state.get(key.lower())
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.debug("Non-numeric measurement for %s: %s", key, value)
            return None

    def prepare_action(self, action: dict, system_state: Optional[dict] = None) -> dict:
        """Enrich an interpreted action with runtime measurements.

        Parameters
        ----------
        action : dict
            Action dictionary produced by a ``visit*Action`` method.
        system_state : dict, optional
            Latest measurements used to compute absolute setpoints.

        Returns
        -------
        dict
            Updated action dictionary containing setpoint metadata and
            measurement keys.
        """
        if not isinstance(action, dict):
            return action

        element_type = action.get("element_type")
        if element_type not in {"load", "generator"}:
            return action

        raw_attribute = action.get("attribute") or action.get("setpoint", {}).get(
            "attribute"
        )
        attribute = self._normalize_attribute_value(raw_attribute)
        action.setdefault("attribute", attribute)

        if action.get("target_spec"):
            refreshed = self._materialize_target(action["target_spec"])
            refreshed_ids = self._normalize_targets(refreshed)
            action["targets"] = refreshed_ids
            action["target"] = (
                refreshed_ids[0] if len(refreshed_ids) == 1 else refreshed_ids
            )

        targets = action.get("targets")
        if not targets:
            targets = self._normalize_targets(action.get("target"))
            action["targets"] = targets
            if len(targets) == 1:
                action["target"] = targets[0]
            elif not targets:
                action["target"] = []

        operation = str(action.get("operation") or "").lower()
        action_type = str(action.get("type") or "").lower()
        setpoint = action.get("setpoint") if isinstance(action.get("setpoint"), dict) else {}
        is_set_action = (
            operation == "set"
            or action_type.startswith("set_")
            or setpoint.get("absolute_value") is not None
            or setpoint.get("absolute_values")
        )
        if not is_set_action and isinstance(action.get("setpoints"), list):
            for entry in action.get("setpoints") or []:
                if isinstance(entry, dict) and entry.get("absolute_value") is not None:
                    is_set_action = True
                    break

        if is_set_action:
            action["operation"] = "set"
            setpoint.setdefault("attribute", attribute)
            absolute_value = setpoint.get("absolute_value")
            if absolute_value is None:
                absolute_value = action.get("value")
            try:
                absolute_value = float(absolute_value) if absolute_value is not None else None
            except (TypeError, ValueError):
                absolute_value = None
            if absolute_value is not None:
                setpoint["absolute_value"] = absolute_value
            action["setpoint"] = setpoint

            setpoints = action.get("setpoints")
            if not isinstance(setpoints, list) or not setpoints:
                setpoints = []
                for target_id in targets:
                    measurement_key = self._measurement_key(element_type, attribute, target_id)
                    setpoints.append(
                        {
                            "id": target_id,
                            "attribute": attribute,
                            "absolute_value": absolute_value,
                            "measurement_key": measurement_key,
                            "operation": "set",
                            "element_type": element_type,
                        }
                    )
            else:
                for entry in setpoints:
                    if not isinstance(entry, dict):
                        continue
                    target_id = entry.get("id")
                    if target_id is None:
                        continue
                    entry.setdefault("attribute", attribute)
                    if entry.get("absolute_value") is None and absolute_value is not None:
                        entry["absolute_value"] = absolute_value
                    entry.setdefault("operation", "set")
                    entry.setdefault("element_type", element_type)
                    if entry.get("measurement_key") is None:
                        measurement_key = self._measurement_key(
                            element_type,
                            entry.get("attribute") or attribute,
                            target_id,
                        )
                        if measurement_key is not None:
                            entry["measurement_key"] = measurement_key

            action["setpoints"] = setpoints
            action["measurement_keys"] = [
                entry.get("measurement_key")
                for entry in setpoints
                if isinstance(entry, dict) and entry.get("measurement_key")
            ]

            if len(setpoints) == 1:
                entry = setpoints[0]
                if isinstance(entry, dict):
                    action["setpoint"].update(
                        {
                            "absolute_value": entry.get("absolute_value"),
                            "measurement_key": entry.get("measurement_key"),
                        }
                    )
            elif setpoints:
                action["setpoint"].update(
                    {
                        "absolute_values": [
                            entry.get("absolute_value")
                            for entry in setpoints
                            if isinstance(entry, dict)
                        ],
                        "measurement_keys": action["measurement_keys"],
                    }
                )

            return action

        delta_percent = None
        if "setpoint" in action:
            delta_percent = action["setpoint"].get("delta_percent")
        if delta_percent is None:
            delta_percent = action.get("percentage")
        try:
            delta_percent = float(delta_percent)
        except (TypeError, ValueError):
            delta_percent = 0.0
        action.setdefault("setpoint", {})
        action["setpoint"]["attribute"] = attribute
        action["setpoint"]["delta_percent"] = float(delta_percent)

        direction = action.get("operation") or (
            "increase"
            if "increase" in str(action.get("type", "")).lower()
            else "decrease"
        )
        action["operation"] = direction
        sign = 1.0 if direction == "increase" else -1.0

        setpoint_entries = []
        measurement_keys = []
        basis_values = []
        absolute_values = []

        for target_id in targets:
            measurement_key = self._measurement_key(element_type, attribute, target_id)
            measurement_keys.append(measurement_key)
            basis = self._lookup_measurement(system_state, measurement_key)
            basis_values.append(basis)
            absolute = None
            if basis is not None:
                absolute = basis * (1.0 + (float(delta_percent) / 100.0 * sign))
            absolute_values.append(absolute)
            setpoint_entries.append(
                {
                    "id": target_id,
                    "attribute": attribute,
                    "delta_percent": float(delta_percent),
                    "basis_value": basis,
                    "absolute_value": absolute,
                    "measurement_key": measurement_key,
                    "operation": direction,
                    "element_type": element_type,
                }
            )

        action["setpoints"] = setpoint_entries
        action["measurement_keys"] = [k for k in measurement_keys if k]

        if len(setpoint_entries) == 1:
            entry = setpoint_entries[0]
            action["setpoint"].update(
                {
                    "basis_value": entry["basis_value"],
                    "absolute_value": entry["absolute_value"],
                    "measurement_key": entry["measurement_key"],
                }
            )
        else:
            action["setpoint"].update(
                {
                    "basis_values": basis_values,
                    "absolute_values": absolute_values,
                    "measurement_keys": action["measurement_keys"],
                }
            )

        return action


__all__ = ["ActionInterpreter"]
