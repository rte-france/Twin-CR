"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def filter_by_regex(components: List[Dict[str, Any]], pattern: str) -> List[str]:
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {pattern}") from e
    matched = [c["id"] for c in components if c.get("id") and regex.search(c["id"])]
    if not matched and pattern == ".*(T|Y|TR).[12].$":
        fallback = re.compile(".*(T|Y|TR).[12]$", re.IGNORECASE)
        matched = [
            c["id"] for c in components if c.get("id") and fallback.match(c["id"])
        ]
    return matched


def filter_by_group(
    components: List[Dict[str, Any]], property_name: str, value: str
) -> List[str]:
    if not components or property_name not in components[0]:
        return []
    if property_name == "tags":
        return [
            c["id"]
            for c in components
            if c.get("id") and value in (c.get("tags", []) or [])
        ]
    return [
        c["id"]
        for c in components
        if c.get("id") and str(c.get(property_name, "")) == str(value)
    ]


def filter_by_property(
    components: List[Dict[str, Any]], property_name: str, operator: str, value: float
) -> List[str]:
    if not components or property_name not in components[0]:
        return []
    out: List[str] = []
    for comp in components:
        cid = comp.get("id")
        if not cid:
            continue
        prop_value = comp.get(property_name, None)
        if prop_value is None:
            continue
        try:
            pv = float(prop_value)
            if operator == "<" and pv < value:
                out.append(cid)
            elif operator == ">" and pv > value:
                out.append(cid)
            elif operator == "<=" and pv <= value:
                out.append(cid)
            elif operator == ">=" and pv >= value:
                out.append(cid)
            elif operator == "==" and abs(pv - value) < 1e-6:
                out.append(cid)
            elif operator == "!=" and abs(pv - value) >= 1e-6:
                out.append(cid)
        except (ValueError, TypeError):
            if operator == "==" and str(prop_value) == str(value):
                out.append(cid)
            elif operator == "!=" and str(prop_value) != str(value):
                out.append(cid)
    return out
