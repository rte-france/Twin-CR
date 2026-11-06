"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Expression parsing and evaluation utilities for the DSL interpreter.
"""

from __future__ import annotations

import logging

from .relationships import RelationshipInterpreter

logger = logging.getLogger(__name__)


class ExpressionInterpreter(RelationshipInterpreter):
    """Parse and evaluate dynamic expressions within the DSL."""

    def visitDynamicExpression(self, ctx):
        return self.visit(ctx.expression())

    def visitExpression(self, ctx):
        return self.visit(ctx.booleanExpr())

    def visitBooleanExpr(self, ctx):
        result = self.visit(ctx.booleanTerm(0))
        for i in range(1, len(ctx.booleanTerm())):
            operator = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.booleanTerm(i))
            result = {"op": operator, "left": result, "right": right}
        return result

    def visitBooleanTerm(self, ctx):
        result = self.visit(ctx.booleanFactor(0))
        for i in range(1, len(ctx.booleanFactor())):
            operator = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.booleanFactor(i))
            result = {"op": operator, "left": result, "right": right}
        return result

    def visitBooleanFactor(self, ctx):
        if ctx.getChild(0).getText() == "(":
            return self.visit(ctx.booleanExpr())
        return self.visit(ctx.booleanAtomic())

    def visitBooleanAtomic(self, ctx):
        if ctx.comparisonExpr():
            return self.visit(ctx.comparisonExpr())
        return self.visit(ctx.booleanLiteral())

    def visitBooleanLiteral(self, ctx):
        return ctx.getText() == "true"

    def visitComparisonExpr(self, ctx):
        left = self.visit(ctx.arithmeticExpr(0))
        operator = ctx.comparison().getText()
        right = self.visit(ctx.arithmeticExpr(1))
        return {"left": left, "op": operator, "right": right}

    def visitArithmeticExpr(self, ctx):
        result = self.visit(ctx.term(0))
        for i in range(1, len(ctx.term())):
            op = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.term(i))
            result = {"op": op, "left": result, "right": right}
        return result

    def visitTerm(self, ctx):
        result = self.visit(ctx.factor(0))
        for i in range(1, len(ctx.factor())):
            op = ctx.getChild(2 * i - 1).getText()
            right = self.visit(ctx.factor(i))
            result = {"op": op, "left": result, "right": right}
        return result

    def visitFactor(self, ctx):
        if ctx.numberWithUnit():
            return self.visit(ctx.numberWithUnit())
        if ctx.variable():
            return self.visit(ctx.variable())
        if ctx.arithmeticExpr():
            return self.visit(ctx.arithmeticExpr())

    def visitNumberWithUnit(self, ctx):
        number = float(ctx.NUMBER().getText())
        if ctx.unit():
            unit = ctx.unit().getText()
            return {"value": number, "unit": unit}
        return number

    def visitVariable(self, ctx):
        first = ctx.getChild(0).getText()
        if first in ["voltage", "frequency"]:
            if ctx.getChildCount() != 4:
                raise ValueError("Invalid variable structure for voltage/frequency")
            component = ctx.getChild(2).getText()
            component_id = ctx.getChild(3).getText()[1:-1]
            return {"type": first, "component": component, "id": component_id}
        if first == "power":
            if ctx.getChildCount() != 5 or ctx.getChild(1).getText() != "flow":
                raise ValueError("Invalid variable structure for power flow")
            component = ctx.getChild(3).getText()
            component_id = ctx.getChild(4).getText()[1:-1]
            return {"type": "power_flow", "component": component, "id": component_id}
        if first in ["active_flow", "reactive_flow"]:
            if ctx.getChildCount() != 4:
                raise ValueError("Invalid variable structure for active/reactive flow")
            component = ctx.getChild(2).getText()
            component_id = ctx.getChild(3).getText()[1:-1]
            return {"type": first, "component": component, "id": component_id}
        raise ValueError(f"Unknown variable type: {first}")

    def evaluate_dynamic_expression(self, expr, system_state):
        """Evaluate a dynamic expression tree in the current system context.

        Parameters
        ----------
        expr : Any
            Expression structure produced by the visitor methods.
        system_state : dict or None
            Mapping of measurement keys to values used during evaluation.

        Returns
        -------
        bool
            Result of the expression, with exceptions converted to ``False``.
        """
        try:
            return self._evaluate_boolean(expr, system_state or {})
        except Exception as exc:
            logger.debug("Failed to evaluate dynamic expression %s: %s", expr, exc)
            return False

    def _evaluate_boolean(self, expr, system_state):
        """Recursively evaluate a boolean expression tree.

        Parameters
        ----------
        expr : Any
            Boolean expression structure returned by visitor helpers.
        system_state : dict
            Measurement dictionary used for variable lookups.

        Returns
        -------
        bool
            Boolean outcome of the expression.
        """
        if isinstance(expr, bool):
            return expr
        if isinstance(expr, dict):
            op = expr.get("op")
            if op in ("and", "or"):
                left = self._evaluate_boolean(expr.get("left"), system_state)
                right = self._evaluate_boolean(expr.get("right"), system_state)
                return left and right if op == "and" else left or right
            if {"left", "right", "op"} <= expr.keys() and op in (
                "<",
                ">",
                "<=",
                ">=",
                "==",
                "!=",
            ):
                left = self._evaluate_arithmetic(expr["left"], system_state)
                right = self._evaluate_arithmetic(expr["right"], system_state)
                return self._compare(op, left, right)
        return bool(expr)

    def _evaluate_arithmetic(self, expr, system_state):
        """Evaluate an arithmetic expression tree.

        Parameters
        ----------
        expr : Any
            Arithmetic expression structure produced by visitor helpers.
        system_state : dict
            Measurement dictionary used for variable lookups.

        Returns
        -------
        float
            Numeric result of the expression.
        """
        if isinstance(expr, (int, float)):
            return float(expr)
        if isinstance(expr, dict):
            if "value" in expr:
                return float(expr["value"])
            op = expr.get("op")
            if op in ("+", "-", "*", "/"):
                left = self._evaluate_arithmetic(expr["left"], system_state)
                right = self._evaluate_arithmetic(expr["right"], system_state)
                if op == "+":
                    return left + right
                if op == "-":
                    return left - right
                if op == "*":
                    return left * right
                if op == "/":
                    return left / right if abs(right) > 1e-9 else float("inf")
            if "type" in expr and "id" in expr:
                return self._lookup_variable(expr, system_state)
        if expr is None:
            return 0.0
        return float(expr)

    def _lookup_variable(self, variable, system_state):
        """Read a measurement referenced by a DSL variable expression.

        Parameters
        ----------
        variable : dict
            Variable descriptor containing ``type``, optional ``component`` and
            ``id`` keys.
        system_state : dict
            Measurement dictionary used for lookup.

        Returns
        -------
        float
            Numeric value of the referenced measurement.

        Raises
        ------
        ValueError
            If the descriptor is incomplete.
        KeyError
            If the requested measurement is missing.
        """
        var_type = variable.get("type")
        component = variable.get("component")
        identifier = variable.get("id")
        if identifier is None or var_type is None:
            raise ValueError("Incomplete variable specification")
        if component:
            key = f"{var_type}:{component}:{identifier}"
        else:
            key = f"{var_type}:{identifier}"
        if key not in system_state:
            raise KeyError(f"Missing value for {key}")
        return float(system_state[key])

    @staticmethod
    def _compare(operator, left, right):
        """Compare two numeric operands using a DSL comparison operator.

        Parameters
        ----------
        operator : str
            Comparison operator token (``<``, ``<=`` and so on).
        left : float
            Left-hand operand.
        right : float
            Right-hand operand.

        Returns
        -------
        bool
            Result of the comparison.

        Raises
        ------
        ValueError
            If ``operator`` is not supported.
        """
        if operator == "<":
            return left < right
        if operator == ">":
            return left > right
        if operator == "<=":
            return left <= right
        if operator == ">=":
            return left >= right
        if operator == "==":
            return abs(left - right) < 1e-6
        if operator == "!=":
            return abs(left - right) >= 1e-6
        raise ValueError(f"Unsupported comparison operator {operator}")


__all__ = ["ExpressionInterpreter"]
