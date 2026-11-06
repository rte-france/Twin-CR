"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

# Generated from gamemaster/core/utils/DSLEngine/antlr/PowerEventDSL.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .PowerEventDSLParser import PowerEventDSLParser
else:
    from PowerEventDSLParser import PowerEventDSLParser

# This class defines a complete generic visitor for a parse tree produced by PowerEventDSLParser.

class PowerEventDSLVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by PowerEventDSLParser#program.
    def visitProgram(self, ctx:PowerEventDSLParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#statement.
    def visitStatement(self, ctx:PowerEventDSLParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#functionDef.
    def visitFunctionDef(self, ctx:PowerEventDSLParser.FunctionDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#functionParamList.
    def visitFunctionParamList(self, ctx:PowerEventDSLParser.FunctionParamListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#setDuration.
    def visitSetDuration(self, ctx:PowerEventDSLParser.SetDurationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#setTimeStep.
    def visitSetTimeStep(self, ctx:PowerEventDSLParser.SetTimeStepContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#eventDef.
    def visitEventDef(self, ctx:PowerEventDSLParser.EventDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#functionStatement.
    def visitFunctionStatement(self, ctx:PowerEventDSLParser.FunctionStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#tagged.
    def visitTagged(self, ctx:PowerEventDSLParser.TaggedContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#executable.
    def visitExecutable(self, ctx:PowerEventDSLParser.ExecutableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#callExpr.
    def visitCallExpr(self, ctx:PowerEventDSLParser.CallExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#verifiedCallExpr.
    def visitVerifiedCallExpr(self, ctx:PowerEventDSLParser.VerifiedCallExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#callArgList.
    def visitCallArgList(self, ctx:PowerEventDSLParser.CallArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#callArg.
    def visitCallArg(self, ctx:PowerEventDSLParser.CallArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#callArgValue.
    def visitCallArgValue(self, ctx:PowerEventDSLParser.CallArgValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#action.
    def visitAction(self, ctx:PowerEventDSLParser.ActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#printAction.
    def visitPrintAction(self, ctx:PowerEventDSLParser.PrintActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#switchAction.
    def visitSwitchAction(self, ctx:PowerEventDSLParser.SwitchActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#lineAction.
    def visitLineAction(self, ctx:PowerEventDSLParser.LineActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#loadAction.
    def visitLoadAction(self, ctx:PowerEventDSLParser.LoadActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#genAction.
    def visitGenAction(self, ctx:PowerEventDSLParser.GenActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#setLoadAction.
    def visitSetLoadAction(self, ctx:PowerEventDSLParser.SetLoadActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#setGenAction.
    def visitSetGenAction(self, ctx:PowerEventDSLParser.SetGenActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#faultAction.
    def visitFaultAction(self, ctx:PowerEventDSLParser.FaultActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#clearFaultAction.
    def visitClearFaultAction(self, ctx:PowerEventDSLParser.ClearFaultActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#networkAction.
    def visitNetworkAction(self, ctx:PowerEventDSLParser.NetworkActionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#linkStatement.
    def visitLinkStatement(self, ctx:PowerEventDSLParser.LinkStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#nodeStatement.
    def visitNodeStatement(self, ctx:PowerEventDSLParser.NodeStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#networkAdjustmentClause.
    def visitNetworkAdjustmentClause(self, ctx:PowerEventDSLParser.NetworkAdjustmentClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#linkClause.
    def visitLinkClause(self, ctx:PowerEventDSLParser.LinkClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#nodeClause.
    def visitNodeClause(self, ctx:PowerEventDSLParser.NodeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#delayClause.
    def visitDelayClause(self, ctx:PowerEventDSLParser.DelayClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#delayFunction.
    def visitDelayFunction(self, ctx:PowerEventDSLParser.DelayFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#dropClause.
    def visitDropClause(self, ctx:PowerEventDSLParser.DropClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#dropFunction.
    def visitDropFunction(self, ctx:PowerEventDSLParser.DropFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#corruptionClause.
    def visitCorruptionClause(self, ctx:PowerEventDSLParser.CorruptionClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#corruptionFunction.
    def visitCorruptionFunction(self, ctx:PowerEventDSLParser.CorruptionFunctionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#corruptionNoiseParams.
    def visitCorruptionNoiseParams(self, ctx:PowerEventDSLParser.CorruptionNoiseParamsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#corruptionZeroParams.
    def visitCorruptionZeroParams(self, ctx:PowerEventDSLParser.CorruptionZeroParamsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#corruptionShiftParams.
    def visitCorruptionShiftParams(self, ctx:PowerEventDSLParser.CorruptionShiftParamsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#corruptionInvertParams.
    def visitCorruptionInvertParams(self, ctx:PowerEventDSLParser.CorruptionInvertParamsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#component.
    def visitComponent(self, ctx:PowerEventDSLParser.ComponentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#componentType.
    def visitComponentType(self, ctx:PowerEventDSLParser.ComponentTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#target.
    def visitTarget(self, ctx:PowerEventDSLParser.TargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#listSpec.
    def visitListSpec(self, ctx:PowerEventDSLParser.ListSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#listItem.
    def visitListItem(self, ctx:PowerEventDSLParser.ListItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#clusterSpec.
    def visitClusterSpec(self, ctx:PowerEventDSLParser.ClusterSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#dynamicClusterSpec.
    def visitDynamicClusterSpec(self, ctx:PowerEventDSLParser.DynamicClusterSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#channelSpec.
    def visitChannelSpec(self, ctx:PowerEventDSLParser.ChannelSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#setRange.
    def visitSetRange(self, ctx:PowerEventDSLParser.SetRangeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#signedNumber.
    def visitSignedNumber(self, ctx:PowerEventDSLParser.SignedNumberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#signedNumericAtom.
    def visitSignedNumericAtom(self, ctx:PowerEventDSLParser.SignedNumericAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#stringAtom.
    def visitStringAtom(self, ctx:PowerEventDSLParser.StringAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#numericAtom.
    def visitNumericAtom(self, ctx:PowerEventDSLParser.NumericAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#relationshipSpec.
    def visitRelationshipSpec(self, ctx:PowerEventDSLParser.RelationshipSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#regexFilter.
    def visitRegexFilter(self, ctx:PowerEventDSLParser.RegexFilterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#groupByFilter.
    def visitGroupByFilter(self, ctx:PowerEventDSLParser.GroupByFilterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#propertyFilter.
    def visitPropertyFilter(self, ctx:PowerEventDSLParser.PropertyFilterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#propertyName.
    def visitPropertyName(self, ctx:PowerEventDSLParser.PropertyNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#timeValue.
    def visitTimeValue(self, ctx:PowerEventDSLParser.TimeValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#timeUnit.
    def visitTimeUnit(self, ctx:PowerEventDSLParser.TimeUnitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#timeSpec.
    def visitTimeSpec(self, ctx:PowerEventDSLParser.TimeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#timeExpr.
    def visitTimeExpr(self, ctx:PowerEventDSLParser.TimeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#nowExpr.
    def visitNowExpr(self, ctx:PowerEventDSLParser.NowExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#intervalSpec.
    def visitIntervalSpec(self, ctx:PowerEventDSLParser.IntervalSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#relativeTimeSpec.
    def visitRelativeTimeSpec(self, ctx:PowerEventDSLParser.RelativeTimeSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#relativeTimeExpr.
    def visitRelativeTimeExpr(self, ctx:PowerEventDSLParser.RelativeTimeExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#relativeTimeValue.
    def visitRelativeTimeValue(self, ctx:PowerEventDSLParser.RelativeTimeValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#relativeIntervalSpec.
    def visitRelativeIntervalSpec(self, ctx:PowerEventDSLParser.RelativeIntervalSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#lawSpec.
    def visitLawSpec(self, ctx:PowerEventDSLParser.LawSpecContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#dynamicExpression.
    def visitDynamicExpression(self, ctx:PowerEventDSLParser.DynamicExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#expression.
    def visitExpression(self, ctx:PowerEventDSLParser.ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#booleanExpr.
    def visitBooleanExpr(self, ctx:PowerEventDSLParser.BooleanExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#booleanTerm.
    def visitBooleanTerm(self, ctx:PowerEventDSLParser.BooleanTermContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#booleanFactor.
    def visitBooleanFactor(self, ctx:PowerEventDSLParser.BooleanFactorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#booleanAtomic.
    def visitBooleanAtomic(self, ctx:PowerEventDSLParser.BooleanAtomicContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#comparisonExpr.
    def visitComparisonExpr(self, ctx:PowerEventDSLParser.ComparisonExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#arithmeticExpr.
    def visitArithmeticExpr(self, ctx:PowerEventDSLParser.ArithmeticExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#term.
    def visitTerm(self, ctx:PowerEventDSLParser.TermContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#factor.
    def visitFactor(self, ctx:PowerEventDSLParser.FactorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#numberWithUnit.
    def visitNumberWithUnit(self, ctx:PowerEventDSLParser.NumberWithUnitContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#comparison.
    def visitComparison(self, ctx:PowerEventDSLParser.ComparisonContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#booleanLiteral.
    def visitBooleanLiteral(self, ctx:PowerEventDSLParser.BooleanLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#variable.
    def visitVariable(self, ctx:PowerEventDSLParser.VariableContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PowerEventDSLParser#unit.
    def visitUnit(self, ctx:PowerEventDSLParser.UnitContext):
        return self.visitChildren(ctx)



del PowerEventDSLParser