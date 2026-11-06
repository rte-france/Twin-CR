"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Control the lifecycle of DSL-based simulations executed by GameMaster.

The simulation controller parses DSL scripts, feeds them into the DSL
interpreter, and exposes helpers to advance the simulation timeline.
"""

import logging
from antlr4 import InputStream, CommonTokenStream
from ...utils.DSLEngine.function_registry import clear_functions

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)


class SimulationController:
    """Manage DSL interpreter state for a single simulation instance."""

    def __init__(self, event_store=None):
        """
        Create a controller bound to an optional event store.

        Args:
            event_store: EventStore-like object used to persist events
                emitted by the DSL interpreter.
        """
        self.interpreter = None
        self.simulation_name = "Default Simulation"  # default value
        self.event_store = event_store
        self.dsl_filename: str | None = None
        self.iidm_artifact_id: str | None = None
        self.completed_point_events: set[str] = set()

    def load_dsl_data(
        self,
        dsl_data: str,
        simulationName: str = "Default Simulation",
        artifact_id: str = "xyz-888",
    ):
        """
        Parse DSL content and start a new simulation.

        Args:
            dsl_data (str): Full DSL program to execute.
            simulationName (str): Human-friendly simulation name logged
                for traceability.
            artifact_id (str): IIDM artifact identifier used by the DSL
                interpreter when resolving components.
        """
        from antlr4 import InputStream, CommonTokenStream
        from ...utils.DSLEngine.antlr.PowerEventDSLLexer import PowerEventDSLLexer
        from ...utils.DSLEngine.antlr.PowerEventDSLParser import PowerEventDSLParser
        from ...utils.DSLEngine import DSLInterpreter

        # Reset event store for this simulation to avoid stale events from prior runs
        try:
            if self.event_store is not None:
                self.event_store.purge_simulation(simulationName)
        except Exception:
            pass
        clear_functions(simulationName)

        self.iidm_artifact_id = artifact_id
        self.interpreter = DSLInterpreter(
            artifact_id=artifact_id,
            event_store=self.event_store,
            simulation_name=simulationName,
        )
        self.completed_point_events.clear()
        input_stream = InputStream(dsl_data)
        lexer = PowerEventDSLLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = PowerEventDSLParser(token_stream)
        tree = parser.program()
        self.interpreter.visit(tree)
        self.interpreter.start_simulation()
        self.simulation_name = simulationName  # store the simulation name
        logger.info(
            "Simulation started: duration=%s sec, time_step=%s sec, name=%s",
            self.interpreter.duration,
            self.interpreter.time_step,
            self.simulation_name,
        )

    def get_next_step(self, new_time: float, system_state=None):
        """
        Retrieve actions for the next simulation step.

        Args:
            new_time (float): Simulation timestamp to advance to.
            system_state: Optional snapshot of system data used by the
                DSL interpreter when evaluating conditions.

        Returns:
            list[dict]: Interpreter actions scheduled for ``new_time``.

        Raises:
            ValueError: If `load_dsl_data` was not called beforehand.
        """
        if system_state is None:
            system_state = {}
        if self.interpreter is None:
            raise ValueError("Simulation not initialized.")
        return self.interpreter.get_current_step_actions(new_time, system_state)
