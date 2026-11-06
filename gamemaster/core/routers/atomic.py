"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Expose real-time endpoints that enqueue DSL snippets for the next step.

The routes in this module allow clients to submit edited DSL fragments
that are normalized and scheduled relative to the current simulation.
"""

import logging
import re
from typing import Optional

from antlr4 import InputStream, CommonTokenStream
from fastapi import APIRouter, HTTPException, Form

from ..domain.controllers.global_instances import (
    get_event_store,
    get_simulation_controller,
)

from ..services.dsl_subscription import ensure_measurements_subscribed
from ..services.dsl_logging import get_dsl_logger
from ..utils.DSLEngine.antlr.PowerEventDSLLexer import PowerEventDSLLexer
from ..utils.DSLEngine.antlr.PowerEventDSLParser import PowerEventDSLParser
from ..utils.DSLEngine import DSLInterpreter
from ..utils.clock import get_current_time

router = APIRouter(tags=["Atomic Update"])

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)


def _force_at_time(snippet: str, t: float) -> str:
    """Force all statements to run at the given time.

    - Splits on ';' and rebuilds each non-empty part as: 'at <t> seconds, <action>;'
    - If a part already starts with 'at ... ,', the prefix is stripped first.
    - Rejects 'when' and 'after' statements for this real-time endpoint.
    """
    parts = [p.strip() for p in snippet.split(";")]
    out = []
    for p in parts:
        if not p:
            continue
        low = p.lower()
        if low.startswith("when ") or low.startswith("after "):
            raise ValueError(
                "'when' and 'after' statements are not allowed in real-time updates. Use direct actions only."
            )
        # Strip an existing leading 'at ...,' prefix if present
        p = re.sub(r"^\s*at\s+.*?,\s*", "", p, flags=re.IGNORECASE)
        out.append(f"at {t} seconds, {p};")
    return "\n".join(out)


@router.post("/rt-user_control_dsl")
async def enqueue_next_step_dsl(dsl: str = Form(...)):
    """Update actions for the next step using DSL commands.

    - Provide one or more DSL action lines (with or without explicit 'at ...').
    - All timestamps supplied by the client are ignored; every action is rescheduled
      to execute at the upcoming simulation step.
    - 'when' and 'after' statements are not allowed in this real-time endpoint.
    """
    try:
        simulation_controller = get_simulation_controller()
        event_store = get_event_store()
        interp = simulation_controller.interpreter
        if interp is None:
            raise HTTPException(status_code=400, detail="Simulation not initialized.")
        if interp.time_step is None:
            raise HTTPException(
                status_code=400, detail="Simulation time step is not defined."
            )

        # Always schedule at the next discrete step based on the absolute clock
        # reported by the simulator requests (fallback to interpreter time if unavailable).
        abs_now = None
        try:
            abs_now = get_current_time(simulation_controller.simulation_name)
        except Exception:
            abs_now = None
        base_time = abs_now if abs_now is not None else interp.current_time
        t_next = min(
            base_time + interp.time_step,
            interp.duration or (base_time + interp.time_step),
        )

        # Prepare a parseable program
        program = _force_at_time(dsl, t_next)
        logger.debug("Next-step DSL program to parse:\n%s", program)

        # Parse and visit with a temporary interpreter that persists to EventStore
        temp = DSLInterpreter(
            artifact_id=interp.artifact_id,
            event_store=event_store,
            simulation_name=simulation_controller.simulation_name,
            event_source="user_dsl",
        )
        input_stream = InputStream(program)
        lexer = PowerEventDSLLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = PowerEventDSLParser(token_stream)
        tree = parser.program()
        temp.visit(tree)  # visitEventDef will enqueue events into EventStore

        if temp.new_measurement_keys:
            # Fire-and-forget to avoid blocking the endpoint on NATS responsiveness.
            async def _subscribe_background():
                try:
                    await ensure_measurements_subscribed(
                        temp.new_measurement_keys,
                        simulation_name=simulation_controller.simulation_name,
                        metadata={"time_passed": t_next},
                    )
                except Exception:
                    logger.debug("Background atomic subscription failed", exc_info=True)

            asyncio.create_task(_subscribe_background())

        dsl_logger = get_dsl_logger()
        if dsl_logger:
            try:
                await dsl_logger.record_append(
                    simulation=simulation_controller.simulation_name,
                    source="user",
                    dsl_text=program,
                    sim_time=t_next,
                    metadata={"original_snippet": dsl},
                )
            except Exception:
                logger.debug("Failed to log DSL append", exc_info=True)

        return {
            "message": "Next-step DSL enqueued",
            "simulationName": simulation_controller.simulation_name,
            "target_time": t_next,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to enqueue next-step DSL: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=400, detail=f"Invalid DSL or processing error: {str(e)}"
        )
