"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Share the DSL execution logger instance across routers and services.
"""

from __future__ import annotations

from typing import Optional

from .dsl_logger import DSLExecutionLogger

_dsl_logger: Optional[DSLExecutionLogger] = None


def set_dsl_logger(logger: Optional[DSLExecutionLogger]) -> None:
    """Store the process-wide DSL execution logger."""

    global _dsl_logger  # pylint: disable=global-statement
    _dsl_logger = logger


def get_dsl_logger() -> Optional[DSLExecutionLogger]:
    """Return the configured DSL execution logger, if any."""

    return _dsl_logger


__all__ = ["get_dsl_logger", "set_dsl_logger"]
