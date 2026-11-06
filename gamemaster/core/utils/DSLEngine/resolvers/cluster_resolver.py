"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Callable

from .relationship_filters import filter_by_regex, filter_by_group, filter_by_property

logger = logging.getLogger(__name__)


class ClusterResolver:
    def __init__(
        self,
        artifact_id: str,
        cache: Dict[str, Any],
        get_properties: Callable[[str, str], List[Dict[str, Any]]],
    ):
        self.artifact_id = artifact_id
        self.cache = cache
        self.get_properties = get_properties

    def resolve(self, relationship: Dict[str, Any]) -> List[str]:
        ctype = relationship["component_type"]
        cache_key = f"{self.artifact_id}:{ctype}"
        if cache_key not in self.cache:
            self.cache[cache_key] = self.get_properties(self.artifact_id, ctype)
        components = self.cache[cache_key]
        if not components:
            return []
        ftype = relationship["filter_type"]
        if ftype == "regex":
            return filter_by_regex(components, relationship["pattern"])
        if ftype == "group_by":
            return filter_by_group(
                components, relationship["property"], relationship["value"]
            )
        if ftype == "property":
            return filter_by_property(
                components,
                relationship["property"],
                relationship["operator"],
                relationship["value"],
            )
        raise ValueError(f"Unknown filter type: {ftype}")
