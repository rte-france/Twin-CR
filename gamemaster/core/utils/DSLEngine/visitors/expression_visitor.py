"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

from ..antlr.PowerEventDSLVisitor import PowerEventDSLVisitor


class ExpressionVisitorMixin(PowerEventDSLVisitor):
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
        if ctx.booleanLiteral():
            return self.visit(ctx.booleanLiteral())
        return self.visit(ctx.comparisonExpr())

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
        elif ctx.variable():
            return self.visit(ctx.variable())
        elif ctx.arithmeticExpr():
            return self.visit(ctx.arithmeticExpr())

    def visitNumberWithUnit(self, ctx):
        number = float(self.visit(ctx.numericAtom()))
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
            id = self.visit(ctx.stringAtom())
            return {"type": first, "component": component, "id": id}
        elif first == "power":
            if ctx.getChildCount() != 5 or ctx.getChild(1).getText() != "flow":
                raise ValueError("Invalid variable structure for power flow")
            component = ctx.getChild(3).getText()
            id = self.visit(ctx.stringAtom())
            return {"type": "power_flow", "component": component, "id": id}
        elif first in ["active_flow", "reactive_flow"]:
            if ctx.getChildCount() != 4:
                raise ValueError("Invalid variable structure for active/reactive flow")
            component = ctx.getChild(2).getText()
            id = self.visit(ctx.stringAtom())
            return {"type": first, "component": component, "id": id}
        else:
            raise ValueError(f"Unknown variable type: {first}")

    # Evaluation
    def evaluate_dynamic_expression(self, expr, system_state):
        try:
            return self._evaluate_boolean(expr, system_state or {})
        except Exception:
            return False

    def _evaluate_boolean(self, expr, system_state):
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
