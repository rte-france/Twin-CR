"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

DSL Engine public API.

Expose the main interpreter while keeping internal modules organized under
`core/`, `iidm/`, and `antlr/`.
"""

from .core.interpreter import DSLInterpreter  # re-export

__all__ = ["DSLInterpreter"]
