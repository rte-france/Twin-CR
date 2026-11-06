"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Visitors that interpret time configuration statements in the DSL.
"""

from __future__ import annotations

import logging

from ..common import to_seconds
from .base import BaseDSLInterpreter

logger = logging.getLogger(__name__)


class TimeConfigurationInterpreter(BaseDSLInterpreter):
    """Handle duration, timestep, and other time-related constructs."""

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

    def visitSetDuration(self, ctx):
        """Record the simulation duration expressed in the DSL.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for the ``setDuration`` grammar rule.

        Raises
        ------
        ValueError
            If the duration was already supplied earlier in the program.
        """
        if self.duration is not None:
            raise ValueError("Duration already set")
        time_value = float(ctx.timeValue().NUMBER().getText())
        time_unit = ctx.timeValue().timeUnit().getText()
        self.duration = to_seconds(time_value, time_unit)
        logger.debug("Duration set to %s seconds", self.duration)

    def visitSetTimeStep(self, ctx):
        """Record the simulation time step expressed in the DSL.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for the ``setTimeStep`` grammar rule.

        Raises
        ------
        ValueError
            If the time step was already supplied earlier in the program.
        """
        if self.time_step is not None:
            raise ValueError("Time step already set")
        time_value = float(ctx.timeValue().NUMBER().getText())
        time_unit = ctx.timeValue().timeUnit().getText()
        self.time_step = to_seconds(time_value, time_unit)
        logger.debug("Time step set to %s seconds", self.time_step)

    def visitTimeSpec(self, ctx):
        """Resolve a time specification expression to either an instant or interval.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``timeSpec``.

        Returns
        -------
        float or dict
            A point-in-time value (seconds) or a dictionary describing an
            interval and the associated progression law.
        """
        if ctx.intervalSpec():
            return self.visit(ctx.intervalSpec())
        return self.visit(ctx.timeExpr())

    def visitIntervalSpec(self, ctx):
        """Translate an interval specification into numeric boundaries.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``intervalSpec``.

        Returns
        -------
        dict
            A dictionary holding the two end points (in seconds) and the
            interpolation law.
        """
        start = self.visit(ctx.timeExpr(0))
        end = self.visit(ctx.timeExpr(1))
        law = "linear"
        if ctx.lawSpec():
            law_text = ctx.lawSpec().getText()
            law = law_text.strip('"')
        logger.debug("Parsed interval: start=%s, end=%s, law=%s", start, end, law)
        return {"interval": (start, end), "law": law}

    def visitTimeExpr(self, ctx):
        """Resolve an absolute or relative time expression."""
        if ctx.timeValue():
            return self.visit(ctx.timeValue())
        if ctx.nowExpr():
            return self.visit(ctx.nowExpr())
        return None

    def visitNowExpr(self, ctx):
        """Resolve now-relative expressions against the interpreter clock."""
        base_time = self._resolve_now()
        if ctx.timeValue() is None:
            return base_time
        offset = self.visit(ctx.timeValue())
        sign_token = ctx.getChild(1).getText()
        if sign_token == "-":
            offset = -offset
        return base_time + offset

    def visitTimeValue(self, ctx):
        """Convert a time literal into seconds.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``timeValue``.

        Returns
        -------
        float
            The literal expressed in seconds.
        """
        time_value = float(ctx.NUMBER().getText())
        time_unit = ctx.timeUnit().getText()
        return to_seconds(time_value, time_unit)


__all__ = ["TimeConfigurationInterpreter"]
