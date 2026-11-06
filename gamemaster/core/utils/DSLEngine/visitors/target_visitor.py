"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

from ..antlr.PowerEventDSLVisitor import PowerEventDSLVisitor


class TargetVisitorMixin(PowerEventDSLVisitor):
    def visitTarget(self, ctx):
        if ctx.stringAtom():
            return self.visit(ctx.stringAtom())
        elif ctx.listSpec():
            return self.visit(ctx.listSpec())
        elif ctx.clusterSpec():
            return self.visit(ctx.clusterSpec())
        elif ctx.dynamicClusterSpec():
            return self.visit(ctx.dynamicClusterSpec())
        raise ValueError("Invalid target specification")

    def visitListSpec(self, ctx):
        return [self.visit(item) for item in ctx.listItem()]

    def visitListItem(self, ctx):
        return self.visit(ctx.stringAtom())

    def visitClusterSpec(self, ctx):
        label = self.visit(ctx.stringAtom()) if ctx.stringAtom() else None
        cluster = self.visit(ctx.listSpec())
        return {"cluster_label": label, "items": cluster}

    def visitDynamicClusterSpec(self, ctx):
        relationship = self.visit(ctx.relationshipSpec())
        return {"type": "dynamic_cluster", "relationship": relationship}

    def visitRelationshipSpec(self, ctx):
        if ctx.regexFilter():
            return self.visit(ctx.regexFilter())
        elif ctx.groupByFilter():
            return self.visit(ctx.groupByFilter())
        elif ctx.propertyFilter():
            return self.visit(ctx.propertyFilter())
        raise ValueError("Invalid relationship specification")

    def visitRegexFilter(self, ctx):
        pattern = self.visit(ctx.stringAtom())
        component_type = ctx.componentType().getText()
        return {
            "filter_type": "regex",
            "pattern": pattern,
            "component_type": component_type,
        }

    def visitGroupByFilter(self, ctx):
        property_name = self.visit(ctx.propertyName())
        value = self.visit(ctx.stringAtom())
        component_type = ctx.componentType().getText()
        return {
            "filter_type": "group_by",
            "property": property_name,
            "value": value,
            "component_type": component_type,
        }

    def visitPropertyFilter(self, ctx):
        property_name = self.visit(ctx.propertyName())
        operator = ctx.comparison().getText()
        value = float(self.visit(ctx.numericAtom()))
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

    def visitPropertyName(self, ctx):
        return self.visit(ctx.stringAtom())

    def _materialize_target(self, target_spec):
        if isinstance(target_spec, dict):
            if target_spec.get("type") == "dynamic_cluster":
                relationship = target_spec.get("relationship")
                if relationship:
                    return self.cluster_resolver.resolve(relationship)
                return []
            if "items" in target_spec:
                return list(target_spec.get("items") or [])
        return target_spec

    @staticmethod
    def _normalize_targets(resolved_target):
        if resolved_target is None:
            return []
        if isinstance(resolved_target, list):
            return [str(t) for t in resolved_target if t is not None]
        if resolved_target == "":
            return []
        return [str(resolved_target)]
