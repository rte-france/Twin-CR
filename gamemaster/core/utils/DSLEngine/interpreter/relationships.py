"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Utilities that expand relationship filters into dynamic clusters.
"""

from __future__ import annotations

import logging
import re

from ..common import get_iidm_properties
from .actions import ActionInterpreter

logger = logging.getLogger(__name__)


class RelationshipInterpreter(ActionInterpreter):
    """Resolve clusters and relationships based on IIDM data."""

    def visitRelationshipSpec(self, ctx):
        """Interpret a relationship specification.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``relationshipSpec``.

        Returns
        -------
        dict
            Canonical representation of the relationship filter.
        """
        if ctx.regexFilter():
            return self.visit(ctx.regexFilter())
        if ctx.groupByFilter():
            return self.visit(ctx.groupByFilter())
        if ctx.propertyFilter():
            return self.visit(ctx.propertyFilter())
        raise ValueError("Invalid relationship specification")

    def visitRegexFilter(self, ctx):
        """Interpret a regex filter declaration.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``regexFilter``.

        Returns
        -------
        dict
            Filter description capturing the pattern and component type.
        """
        pattern = ctx.STRING().getText()[1:-1]
        component_type = ctx.componentType().getText()
        return {
            "filter_type": "regex",
            "pattern": pattern,
            "component_type": component_type,
        }

    def visitGroupByFilter(self, ctx):
        """Interpret a group-by filter declaration.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``groupByFilter``.

        Returns
        -------
        dict
            Filter description capturing the property and desired value.
        """
        property_name = ctx.propertyName().getText()[1:-1]
        value = ctx.STRING().getText()[1:-1]
        component_type = ctx.componentType().getText()
        return {
            "filter_type": "group_by",
            "property": property_name,
            "value": value,
            "component_type": component_type,
        }

    def visitPropertyFilter(self, ctx):
        """Interpret a property comparison filter.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree context for ``propertyFilter``.

        Returns
        -------
        dict
            Filter description containing the property, comparison operator,
            threshold and optional unit.
        """
        property_name = ctx.propertyName().getText()[1:-1]
        operator = ctx.comparison().getText()
        value = float(ctx.NUMBER().getText())
        unit = ctx.unit().getText() if ctx.unit() else None
        component_type = ctx.componentType().getText()
        return {
            "filter_type": "property",
            "property": property_name,
            "operator": operator,
            "value": value,
            "unit": unit,
            "component_type": component_type,
        }

    def resolve_dynamic_cluster(self, relationship):
        """Construct a list of components that satisfy a relationship filter.

        Parameters
        ----------
        relationship : dict
            Structured filter definition returned by the ``visit*Filter``
            helpers.

        Returns
        -------
        list[str]
            Matching component identifiers (possibly empty).

        Raises
        ------
        ValueError
            If a regex pattern is invalid.
        """
        component_type = relationship["component_type"]
        cache_key = f"{self.artifact_id}:{component_type}"
        if cache_key not in self.iidm_cache:
            logger.debug("Cache miss for %s, fetching properties", cache_key)
            self.iidm_cache[cache_key] = get_iidm_properties(
                self.artifact_id, component_type
            )
        else:
            logger.debug("Cache hit for %s", cache_key)
        components = self.iidm_cache[cache_key]
        if not components:
            logger.debug(
                "No components available for %s; proceeding without dynamic resolution",
                cache_key,
            )
        logger.debug(
            "Resolving dynamic cluster for %s: %d components available",
            component_type,
            len(components),
        )
        logger.debug(
            "Available component IDs: %s",
            [comp.get("id", "missing_id") for comp in components],
        )

        missing_id_count = sum(
            1 for comp in components if not comp.get("id") or comp["id"] == ""
        )
        if missing_id_count:
            logger.warning(
                "%d components of type %s have missing or empty 'id' attributes",
                missing_id_count,
                component_type,
            )

        filter_type = relationship["filter_type"]
        if filter_type == "regex":
            pattern = relationship["pattern"]
            logger.debug("Applying regex filter: pattern=%s", pattern)
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                matched_ids = [
                    comp["id"]
                    for comp in components
                    if comp.get("id") and comp["id"] != "" and regex.search(comp["id"])
                ]
                logger.debug("Regex matched %d IDs: %s", len(matched_ids), matched_ids)

                if not matched_ids and pattern == ".*(T|Y|TR).[12].$":
                    fallback_pattern = ".*(T|Y|TR).[12]$"
                    logger.debug(
                        "No matches with original pattern, trying fallback regex: %s",
                        fallback_pattern,
                    )
                    fallback_regex = re.compile(fallback_pattern, re.IGNORECASE)
                    matched_ids = [
                        comp["id"]
                        for comp in components
                        if comp.get("id")
                        and comp["id"] != ""
                        and fallback_regex.match(comp["id"])
                    ]
                    logger.debug(
                        "Fallback regex matched %d IDs: %s",
                        len(matched_ids),
                        matched_ids,
                    )

                return matched_ids
            except re.error as e:
                logger.error("Invalid regex pattern '%s': %s", pattern, e)
                raise ValueError(f"Invalid regex pattern: {pattern}")
        elif filter_type == "group_by":
            property_name = relationship["property"]
            value = relationship["value"]
            logger.debug(
                "Applying group_by filter: property=%s, value=%s", property_name, value
            )
            if not components or property_name not in components[0]:
                logger.warning(
                    "Property '%s' not found in components of type %s",
                    property_name,
                    component_type,
                )
                return []
            if property_name == "tags":
                matched_ids = [
                    comp["id"]
                    for comp in components
                    if comp.get("id")
                    and comp["id"] != ""
                    and value in (comp.get("tags", []) or [])
                ]
            else:
                matched_ids = [
                    comp["id"]
                    for comp in components
                    if comp.get("id")
                    and comp["id"] != ""
                    and str(comp.get(property_name, "")) == str(value)
                ]
            logger.debug("Group_by matched %d IDs: %s", len(matched_ids), matched_ids)
            logger.debug(
                "Available %s values: %s",
                property_name,
                [comp.get(property_name, "") for comp in components],
            )
            return matched_ids
        elif filter_type == "property":
            property_name = relationship["property"]
            operator = relationship["operator"]
            value = relationship["value"]
            logger.debug(
                "Applying property filter: property=%s, operator=%s, value=%s",
                property_name,
                operator,
                value,
            )
            if not components or property_name not in components[0]:
                logger.warning(
                    "Property '%s' not found in components of type %s",
                    property_name,
                    component_type,
                )
                return []
            filtered = []
            skipped = 0
            for comp in components:
                if not comp.get("id") or comp["id"] == "":
                    skipped += 1
                    continue
                prop_value = comp.get(property_name, None)
                if prop_value is None:
                    logger.debug(
                        "Skipping component %s: %s is missing",
                        comp.get("id", "unknown"),
                        property_name,
                    )
                    skipped += 1
                    continue
                logger.debug(
                    "Checking component %s: %s=%s",
                    comp["id"],
                    property_name,
                    prop_value,
                )
                try:
                    prop_value = float(prop_value)
                    if operator == "<" and prop_value < value:
                        filtered.append(comp["id"])
                    elif operator == ">" and prop_value > value:
                        filtered.append(comp["id"])
                    elif operator == "<=" and prop_value <= value:
                        filtered.append(comp["id"])
                    elif operator == ">=" and prop_value >= value:
                        filtered.append(comp["id"])
                    elif operator == "==" and abs(prop_value - value) < 1e-6:
                        filtered.append(comp["id"])
                    elif operator == "!=" and abs(prop_value - value) >= 1e-6:
                        filtered.append(comp["id"])
                except (ValueError, TypeError):
                    if operator == "==" and str(prop_value) == str(value):
                        filtered.append(comp["id"])
                    elif operator == "!=" and str(prop_value) != str(value):
                        filtered.append(comp["id"])
                    else:
                        logger.debug(
                            "Skipping non-numeric %s for %s: %s",
                            property_name,
                            comp["id"],
                            prop_value,
                        )
                        skipped += 1
            if skipped:
                logger.warning(
                    "Skipped %d components due to missing or non-numeric %s values",
                    skipped,
                    property_name,
                )
            logger.debug("Property filter matched %d IDs: %s", len(filtered), filtered)
            logger.debug(
                "Available %s values: %s",
                property_name,
                [comp.get(property_name, None) for comp in components],
            )
            return filtered
        raise ValueError(f"Unknown filter type: {filter_type}")


__all__ = ["RelationshipInterpreter"]
