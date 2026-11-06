"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Component type normalization utilities for IIDM access.
"""

from __future__ import annotations

from ..core.constants import COMPONENT_MAP


def normalize_component_type(component_type: str) -> str:
    """Return the element key for a given component type string.

    Falls back to the original value if no mapping is found.
    """
    normalized = (component_type or "").strip()
    key = COMPONENT_MAP.get(normalized)
    if key is None:
        key = COMPONENT_MAP.get(normalized.lower(), normalized)
    return key
