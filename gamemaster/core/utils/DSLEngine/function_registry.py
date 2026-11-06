"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict, List, Optional


@dataclass(frozen=True)
class FunctionDefinition:
    name: str
    params: List[str]
    statements: tuple
    source_text: str


_LOCK = RLock()
_REGISTRY: Dict[str, Dict[str, FunctionDefinition]] = {}


def load_functions(simulation_name: Optional[str]) -> Dict[str, FunctionDefinition]:
    if not simulation_name:
        return {}
    with _LOCK:
        return dict(_REGISTRY.get(simulation_name, {}))


def store_functions(
    simulation_name: Optional[str],
    definitions: Dict[str, FunctionDefinition],
) -> None:
    if not simulation_name or not definitions:
        return
    with _LOCK:
        current = dict(_REGISTRY.get(simulation_name, {}))
        current.update(definitions)
        _REGISTRY[simulation_name] = current


def clear_functions(simulation_name: Optional[str]) -> None:
    if not simulation_name:
        return
    with _LOCK:
        _REGISTRY.pop(simulation_name, None)
