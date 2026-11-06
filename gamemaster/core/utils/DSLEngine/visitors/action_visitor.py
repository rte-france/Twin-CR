"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..antlr.PowerEventDSLVisitor import PowerEventDSLVisitor
from ..common import to_seconds
from ..simulation.action_processor import ActionProcessor as AP


class ActionVisitorMixin(PowerEventDSLVisitor):
    @staticmethod
    def _string_text(node) -> str:
        raw = node.getText()
        if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            return raw[1:-1]
        return raw

    def visitSwitchAction(self, ctx):
        operation = ctx.getChild(0).getText()
        id = self.visit(ctx.stringAtom())
        return {"type": f"{operation}_switch", "id": id}

    def visitLineAction(self, ctx):
        operation = ctx.getChild(0).getText()
        id = self.visit(ctx.stringAtom())
        return {"type": f"{operation}_line", "id": id}

    def visitLoadAction(self, ctx):
        operation = ctx.getChild(0).getText()
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        percentage = float(self.visit(ctx.numericAtom()))
        attribute = AP.parse_channel(ctx.channelSpec())
        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            AP.measurement_key("load", attribute, tid) for tid in target_ids if tid
        ]
        action = {
            "type": f"{operation}_load",
            "target": simplified_target,
            "targets": target_ids,
            "percentage": percentage,
            "attribute": attribute,
            "element_type": "load",
            "operation": operation,
            "setpoint": {"attribute": attribute, "delta_percent": percentage},
        }
        action["target_percentage"] = percentage
        if isinstance(target_spec, dict) and target_spec:
            action["target_spec"] = target_spec
        if measurement_keys:
            self.new_measurement_keys.update(measurement_keys)
            action["measurement_keys"] = measurement_keys
        return action

    def visitGenAction(self, ctx):
        operation = ctx.getChild(0).getText()
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        percentage = float(self.visit(ctx.numericAtom()))
        attribute = AP.parse_channel(ctx.channelSpec())
        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            AP.measurement_key("generator", attribute, tid) for tid in target_ids if tid
        ]
        action = {
            "type": f"{operation}_generator",
            "target": simplified_target,
            "targets": target_ids,
            "percentage": percentage,
            "attribute": attribute,
            "element_type": "generator",
            "operation": operation,
            "setpoint": {"attribute": attribute, "delta_percent": percentage},
        }
        action["target_percentage"] = percentage
        if isinstance(target_spec, dict) and target_spec:
            action["target_spec"] = target_spec
        if measurement_keys:
            self.new_measurement_keys.update(measurement_keys)
            action["measurement_keys"] = measurement_keys
        return action

    def visitSetLoadAction(self, ctx):
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        range_ctx = ctx.setRange()
        numbers = range_ctx.signedNumber()
        absolute_value = float(self.visit(numbers[-1]))
        from_value = float(self.visit(numbers[0])) if len(numbers) > 1 else None
        attribute = AP.parse_channel(ctx.channelSpec())
        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            AP.measurement_key("load", attribute, tid) for tid in target_ids if tid
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
        return action

    def visitSetGenAction(self, ctx):
        target_spec = self.visit(ctx.target())
        resolved_target = self._materialize_target(target_spec)
        target_ids = self._normalize_targets(resolved_target)
        range_ctx = ctx.setRange()
        numbers = range_ctx.signedNumber()
        absolute_value = float(self.visit(numbers[-1]))
        from_value = float(self.visit(numbers[0])) if len(numbers) > 1 else None
        attribute = AP.parse_channel(ctx.channelSpec())
        simplified_target = target_ids[0] if len(target_ids) == 1 else target_ids
        measurement_keys = [
            AP.measurement_key("generator", attribute, tid) for tid in target_ids if tid
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
        return action

    def visitFaultAction(self, ctx):
        component_type = ctx.component().componentType().getText()
        id = self.visit(ctx.component().stringAtom())
        return {"type": "apply_fault", "component_type": component_type, "id": id}

    def visitClearFaultAction(self, ctx):
        component_type = ctx.component().componentType().getText()
        id = self.visit(ctx.component().stringAtom())
        return {"type": "clear_fault", "component_type": component_type, "id": id}

    def visitPrintAction(self, ctx):
        message = ctx.STRING().getText()[1:-1]
        return {"type": "print", "message": message}

    def visitNetworkAction(self, ctx):
        links = self.visit(ctx.linkStatement()) if ctx.linkStatement() else []
        nodes = self.visit(ctx.nodeStatement()) if ctx.nodeStatement() else []

        action: Dict[str, Any] = {
            "type": "change_network_characteristics",
            "links": links,
            "nodes": nodes,
        }
        delay_func: Optional[Dict[str, Any]] = None
        drop_func: Optional[Dict[str, Any]] = None
        corruption_funcs: List[Dict[str, Any]] = []

        for clause_ctx in ctx.networkAdjustmentClause():
            kind, value = self.visit(clause_ctx)
            if kind == "delay":
                if delay_func is not None:
                    raise ValueError(
                        "Delay function specified more than once in network characteristic change."
                    )
                delay_func = value
            elif kind == "drop":
                if drop_func is not None:
                    raise ValueError(
                        "Drop function specified more than once in network characteristic change."
                    )
                drop_func = value
            elif kind == "corruption":
                corruption_funcs.append(value)

        if delay_func is not None:
            action["delay_function"] = delay_func
        if drop_func is not None:
            action["drop_function"] = drop_func
        if corruption_funcs:
            action["corruption_functions"] = corruption_funcs

        return action

    def visitLinkStatement(self, ctx):
        return [self.visit(link_ctx) for link_ctx in ctx.linkClause()]

    def visitNodeStatement(self, ctx):
        return [self.visit(node_ctx) for node_ctx in ctx.nodeClause()]

    def visitNetworkAdjustmentClause(self, ctx):
        if ctx.delayClause():
            return "delay", self.visit(ctx.delayClause())
        if ctx.dropClause():
            return "drop", self.visit(ctx.dropClause())
        if ctx.corruptionClause():
            return "corruption", self.visit(ctx.corruptionClause())
        raise ValueError("Unsupported network adjustment clause.")

    def visitLinkClause(self, ctx):
        src = self._string_text(ctx.STRING(0))
        dst = self._string_text(ctx.STRING(1))
        return {"from": src, "to": dst}

    def visitNodeClause(self, ctx):
        return self._string_text(ctx.STRING())

    def visitDelayClause(self, ctx):
        return self.visit(ctx.delayFunction())

    def visitDelayFunction(self, ctx):
        head = ctx.getChild(0).getText()
        if head == "fixed":
            value = float(self.visit(ctx.numericAtom(0)))
            unit = ctx.timeUnit(0).getText() if ctx.timeUnit() else None
            return {
                "type": "fixed",
                "delay": self._convert_to_seconds(value, unit),
            }
        if head == "gauss":
            mean_val = float(self.visit(ctx.numericAtom(0)))
            std_val = float(self.visit(ctx.numericAtom(1)))
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
            probability = float(self.visit(ctx.numericAtom()))
            return {"type": "random", "value": probability}
        raise ValueError("Unknown drop function type.")

    def visitCorruptionClause(self, ctx):
        return self.visit(ctx.corruptionFunction())

    def visitCorruptionFunction(self, ctx):
        head = ctx.getChild(0).getText()
        if head == "none":
            likelihood = 1.0
            if ctx.numericAtom():
                likelihood = float(self.visit(ctx.numericAtom(0)))
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
                likelihood = float(self.visit(children[idx + 1]))
                idx += 2
            elif token == "range":
                noise_min = float(self.visit(children[idx + 1]))
                if children[idx + 2].getText() != "to":
                    raise ValueError('Noise range must use "to" delimiter.')
                noise_max = float(self.visit(children[idx + 3]))
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
                likelihood = float(self.visit(children[idx + 1]))
                idx += 2
            elif token == "value":
                zero_value = float(self.visit(children[idx + 1]))
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
                likelihood = float(self.visit(children[idx + 1]))
                idx += 2
            elif token == "by":
                shift_value = float(self.visit(children[idx + 1]))
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
                likelihood = float(self.visit(children[idx + 1]))
                idx += 2
            elif token == "by":
                invert_factor = float(self.visit(children[idx + 1]))
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
