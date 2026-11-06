"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Helpers that resolve DSL target specifications into concrete identifiers.
"""

from __future__ import annotations

import logging

from .events import EventDefinitionInterpreter

logger = logging.getLogger(__name__)


class TargetResolutionInterpreter(EventDefinitionInterpreter):
    """Resolve target specifications into concrete component identifiers."""

    def visitTarget(self, ctx):
        """Interpret a ``target`` clause.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree node for ``target``.

        Returns
        -------
        str or list or dict
            A single identifier, a list of identifiers, or a cluster descriptor
            ready for further materialisation.
        """
        if ctx.STRING():
            return ctx.STRING().getText()[1:-1]
        if ctx.listSpec():
            return self.visit(ctx.listSpec())
        if ctx.clusterSpec():
            return self.visit(ctx.clusterSpec())
        if ctx.dynamicClusterSpec():
            return self.visit(ctx.dynamicClusterSpec())
        raise ValueError("Invalid target specification")

    def visitListSpec(self, ctx):
        """Resolve a list of literal targets.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree for ``listSpec``.

        Returns
        -------
        list[str]
            Identifiers extracted from the literal list specification.
        """
        return [item.getText()[1:-1] for item in ctx.listItem()]

    def visitClusterSpec(self, ctx):
        """Resolve a static cluster declaration.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree for ``clusterSpec``.

        Returns
        -------
        dict
            Cluster metadata containing the optional label and item sequence.
        """
        label = ctx.STRING().getText()[1:-1] if ctx.STRING() else None
        cluster = self.visit(ctx.listSpec())
        return {"cluster_label": label, "items": cluster}

    def visitDynamicClusterSpec(self, ctx):
        """Resolve a dynamic cluster declaration.

        Parameters
        ----------
        ctx : antlr4.ParserRuleContext
            Parse tree for ``dynamicClusterSpec``.

        Returns
        -------
        dict
            Specification that instructs later stages how to build the cluster
            on demand.
        """
        relationship = self.visit(ctx.relationshipSpec())
        return {"type": "dynamic_cluster", "relationship": relationship}

    def _materialize_target(self, target_spec):
        """Evaluate a target specification into basic identifiers.

        Parameters
        ----------
        target_spec : Any
            Output of ``visitTarget`` or a derived helper.

        Returns
        -------
        Any
            Concrete identifier(s) or the untouched specification when more
            processing is required later.
        """
        if isinstance(target_spec, dict):
            if target_spec.get("type") == "dynamic_cluster":
                relationship = target_spec.get("relationship")
                if relationship:
                    return self.resolve_dynamic_cluster(relationship)
                return []
            if "items" in target_spec:
                return list(target_spec.get("items") or [])
        return target_spec

    @staticmethod
    def _normalize_targets(resolved_target):
        """Normalise resolved targets into a list of string identifiers.

        Parameters
        ----------
        resolved_target : Any
            Single identifier, list of identifiers, or empty sentinel.

        Returns
        -------
        list[str]
            Clean list where ``None`` or empty entries have been removed.
        """
        if resolved_target is None:
            return []
        if isinstance(resolved_target, list):
            return [str(t) for t in resolved_target if t is not None]
        if resolved_target == "":
            return []
        return [str(resolved_target)]


__all__ = ["TargetResolutionInterpreter"]
