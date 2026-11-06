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

# This class defines a complete listener for a parse tree produced by PowerEventDSLParser.
class PowerEventDSLListener(ParseTreeListener):

    # Enter a parse tree produced by PowerEventDSLParser#program.
    def enterProgram(self, ctx:PowerEventDSLParser.ProgramContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#program.
    def exitProgram(self, ctx:PowerEventDSLParser.ProgramContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#statement.
    def enterStatement(self, ctx:PowerEventDSLParser.StatementContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#statement.
    def exitStatement(self, ctx:PowerEventDSLParser.StatementContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#functionDef.
    def enterFunctionDef(self, ctx:PowerEventDSLParser.FunctionDefContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#functionDef.
    def exitFunctionDef(self, ctx:PowerEventDSLParser.FunctionDefContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#functionParamList.
    def enterFunctionParamList(self, ctx:PowerEventDSLParser.FunctionParamListContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#functionParamList.
    def exitFunctionParamList(self, ctx:PowerEventDSLParser.FunctionParamListContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#setDuration.
    def enterSetDuration(self, ctx:PowerEventDSLParser.SetDurationContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#setDuration.
    def exitSetDuration(self, ctx:PowerEventDSLParser.SetDurationContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#setTimeStep.
    def enterSetTimeStep(self, ctx:PowerEventDSLParser.SetTimeStepContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#setTimeStep.
    def exitSetTimeStep(self, ctx:PowerEventDSLParser.SetTimeStepContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#eventDef.
    def enterEventDef(self, ctx:PowerEventDSLParser.EventDefContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#eventDef.
    def exitEventDef(self, ctx:PowerEventDSLParser.EventDefContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#functionStatement.
    def enterFunctionStatement(self, ctx:PowerEventDSLParser.FunctionStatementContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#functionStatement.
    def exitFunctionStatement(self, ctx:PowerEventDSLParser.FunctionStatementContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#tagged.
    def enterTagged(self, ctx:PowerEventDSLParser.TaggedContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#tagged.
    def exitTagged(self, ctx:PowerEventDSLParser.TaggedContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#executable.
    def enterExecutable(self, ctx:PowerEventDSLParser.ExecutableContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#executable.
    def exitExecutable(self, ctx:PowerEventDSLParser.ExecutableContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#callExpr.
    def enterCallExpr(self, ctx:PowerEventDSLParser.CallExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#callExpr.
    def exitCallExpr(self, ctx:PowerEventDSLParser.CallExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#verifiedCallExpr.
    def enterVerifiedCallExpr(self, ctx:PowerEventDSLParser.VerifiedCallExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#verifiedCallExpr.
    def exitVerifiedCallExpr(self, ctx:PowerEventDSLParser.VerifiedCallExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#callArgList.
    def enterCallArgList(self, ctx:PowerEventDSLParser.CallArgListContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#callArgList.
    def exitCallArgList(self, ctx:PowerEventDSLParser.CallArgListContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#callArg.
    def enterCallArg(self, ctx:PowerEventDSLParser.CallArgContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#callArg.
    def exitCallArg(self, ctx:PowerEventDSLParser.CallArgContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#callArgValue.
    def enterCallArgValue(self, ctx:PowerEventDSLParser.CallArgValueContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#callArgValue.
    def exitCallArgValue(self, ctx:PowerEventDSLParser.CallArgValueContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#action.
    def enterAction(self, ctx:PowerEventDSLParser.ActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#action.
    def exitAction(self, ctx:PowerEventDSLParser.ActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#printAction.
    def enterPrintAction(self, ctx:PowerEventDSLParser.PrintActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#printAction.
    def exitPrintAction(self, ctx:PowerEventDSLParser.PrintActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#switchAction.
    def enterSwitchAction(self, ctx:PowerEventDSLParser.SwitchActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#switchAction.
    def exitSwitchAction(self, ctx:PowerEventDSLParser.SwitchActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#lineAction.
    def enterLineAction(self, ctx:PowerEventDSLParser.LineActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#lineAction.
    def exitLineAction(self, ctx:PowerEventDSLParser.LineActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#loadAction.
    def enterLoadAction(self, ctx:PowerEventDSLParser.LoadActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#loadAction.
    def exitLoadAction(self, ctx:PowerEventDSLParser.LoadActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#genAction.
    def enterGenAction(self, ctx:PowerEventDSLParser.GenActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#genAction.
    def exitGenAction(self, ctx:PowerEventDSLParser.GenActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#setLoadAction.
    def enterSetLoadAction(self, ctx:PowerEventDSLParser.SetLoadActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#setLoadAction.
    def exitSetLoadAction(self, ctx:PowerEventDSLParser.SetLoadActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#setGenAction.
    def enterSetGenAction(self, ctx:PowerEventDSLParser.SetGenActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#setGenAction.
    def exitSetGenAction(self, ctx:PowerEventDSLParser.SetGenActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#faultAction.
    def enterFaultAction(self, ctx:PowerEventDSLParser.FaultActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#faultAction.
    def exitFaultAction(self, ctx:PowerEventDSLParser.FaultActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#clearFaultAction.
    def enterClearFaultAction(self, ctx:PowerEventDSLParser.ClearFaultActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#clearFaultAction.
    def exitClearFaultAction(self, ctx:PowerEventDSLParser.ClearFaultActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#networkAction.
    def enterNetworkAction(self, ctx:PowerEventDSLParser.NetworkActionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#networkAction.
    def exitNetworkAction(self, ctx:PowerEventDSLParser.NetworkActionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#linkStatement.
    def enterLinkStatement(self, ctx:PowerEventDSLParser.LinkStatementContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#linkStatement.
    def exitLinkStatement(self, ctx:PowerEventDSLParser.LinkStatementContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#nodeStatement.
    def enterNodeStatement(self, ctx:PowerEventDSLParser.NodeStatementContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#nodeStatement.
    def exitNodeStatement(self, ctx:PowerEventDSLParser.NodeStatementContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#networkAdjustmentClause.
    def enterNetworkAdjustmentClause(self, ctx:PowerEventDSLParser.NetworkAdjustmentClauseContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#networkAdjustmentClause.
    def exitNetworkAdjustmentClause(self, ctx:PowerEventDSLParser.NetworkAdjustmentClauseContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#linkClause.
    def enterLinkClause(self, ctx:PowerEventDSLParser.LinkClauseContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#linkClause.
    def exitLinkClause(self, ctx:PowerEventDSLParser.LinkClauseContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#nodeClause.
    def enterNodeClause(self, ctx:PowerEventDSLParser.NodeClauseContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#nodeClause.
    def exitNodeClause(self, ctx:PowerEventDSLParser.NodeClauseContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#delayClause.
    def enterDelayClause(self, ctx:PowerEventDSLParser.DelayClauseContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#delayClause.
    def exitDelayClause(self, ctx:PowerEventDSLParser.DelayClauseContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#delayFunction.
    def enterDelayFunction(self, ctx:PowerEventDSLParser.DelayFunctionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#delayFunction.
    def exitDelayFunction(self, ctx:PowerEventDSLParser.DelayFunctionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#dropClause.
    def enterDropClause(self, ctx:PowerEventDSLParser.DropClauseContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#dropClause.
    def exitDropClause(self, ctx:PowerEventDSLParser.DropClauseContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#dropFunction.
    def enterDropFunction(self, ctx:PowerEventDSLParser.DropFunctionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#dropFunction.
    def exitDropFunction(self, ctx:PowerEventDSLParser.DropFunctionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#corruptionClause.
    def enterCorruptionClause(self, ctx:PowerEventDSLParser.CorruptionClauseContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#corruptionClause.
    def exitCorruptionClause(self, ctx:PowerEventDSLParser.CorruptionClauseContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#corruptionFunction.
    def enterCorruptionFunction(self, ctx:PowerEventDSLParser.CorruptionFunctionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#corruptionFunction.
    def exitCorruptionFunction(self, ctx:PowerEventDSLParser.CorruptionFunctionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#corruptionNoiseParams.
    def enterCorruptionNoiseParams(self, ctx:PowerEventDSLParser.CorruptionNoiseParamsContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#corruptionNoiseParams.
    def exitCorruptionNoiseParams(self, ctx:PowerEventDSLParser.CorruptionNoiseParamsContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#corruptionZeroParams.
    def enterCorruptionZeroParams(self, ctx:PowerEventDSLParser.CorruptionZeroParamsContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#corruptionZeroParams.
    def exitCorruptionZeroParams(self, ctx:PowerEventDSLParser.CorruptionZeroParamsContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#corruptionShiftParams.
    def enterCorruptionShiftParams(self, ctx:PowerEventDSLParser.CorruptionShiftParamsContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#corruptionShiftParams.
    def exitCorruptionShiftParams(self, ctx:PowerEventDSLParser.CorruptionShiftParamsContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#corruptionInvertParams.
    def enterCorruptionInvertParams(self, ctx:PowerEventDSLParser.CorruptionInvertParamsContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#corruptionInvertParams.
    def exitCorruptionInvertParams(self, ctx:PowerEventDSLParser.CorruptionInvertParamsContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#component.
    def enterComponent(self, ctx:PowerEventDSLParser.ComponentContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#component.
    def exitComponent(self, ctx:PowerEventDSLParser.ComponentContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#componentType.
    def enterComponentType(self, ctx:PowerEventDSLParser.ComponentTypeContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#componentType.
    def exitComponentType(self, ctx:PowerEventDSLParser.ComponentTypeContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#target.
    def enterTarget(self, ctx:PowerEventDSLParser.TargetContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#target.
    def exitTarget(self, ctx:PowerEventDSLParser.TargetContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#listSpec.
    def enterListSpec(self, ctx:PowerEventDSLParser.ListSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#listSpec.
    def exitListSpec(self, ctx:PowerEventDSLParser.ListSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#listItem.
    def enterListItem(self, ctx:PowerEventDSLParser.ListItemContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#listItem.
    def exitListItem(self, ctx:PowerEventDSLParser.ListItemContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#clusterSpec.
    def enterClusterSpec(self, ctx:PowerEventDSLParser.ClusterSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#clusterSpec.
    def exitClusterSpec(self, ctx:PowerEventDSLParser.ClusterSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#dynamicClusterSpec.
    def enterDynamicClusterSpec(self, ctx:PowerEventDSLParser.DynamicClusterSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#dynamicClusterSpec.
    def exitDynamicClusterSpec(self, ctx:PowerEventDSLParser.DynamicClusterSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#channelSpec.
    def enterChannelSpec(self, ctx:PowerEventDSLParser.ChannelSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#channelSpec.
    def exitChannelSpec(self, ctx:PowerEventDSLParser.ChannelSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#setRange.
    def enterSetRange(self, ctx:PowerEventDSLParser.SetRangeContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#setRange.
    def exitSetRange(self, ctx:PowerEventDSLParser.SetRangeContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#signedNumber.
    def enterSignedNumber(self, ctx:PowerEventDSLParser.SignedNumberContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#signedNumber.
    def exitSignedNumber(self, ctx:PowerEventDSLParser.SignedNumberContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#signedNumericAtom.
    def enterSignedNumericAtom(self, ctx:PowerEventDSLParser.SignedNumericAtomContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#signedNumericAtom.
    def exitSignedNumericAtom(self, ctx:PowerEventDSLParser.SignedNumericAtomContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#stringAtom.
    def enterStringAtom(self, ctx:PowerEventDSLParser.StringAtomContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#stringAtom.
    def exitStringAtom(self, ctx:PowerEventDSLParser.StringAtomContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#numericAtom.
    def enterNumericAtom(self, ctx:PowerEventDSLParser.NumericAtomContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#numericAtom.
    def exitNumericAtom(self, ctx:PowerEventDSLParser.NumericAtomContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#relationshipSpec.
    def enterRelationshipSpec(self, ctx:PowerEventDSLParser.RelationshipSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#relationshipSpec.
    def exitRelationshipSpec(self, ctx:PowerEventDSLParser.RelationshipSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#regexFilter.
    def enterRegexFilter(self, ctx:PowerEventDSLParser.RegexFilterContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#regexFilter.
    def exitRegexFilter(self, ctx:PowerEventDSLParser.RegexFilterContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#groupByFilter.
    def enterGroupByFilter(self, ctx:PowerEventDSLParser.GroupByFilterContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#groupByFilter.
    def exitGroupByFilter(self, ctx:PowerEventDSLParser.GroupByFilterContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#propertyFilter.
    def enterPropertyFilter(self, ctx:PowerEventDSLParser.PropertyFilterContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#propertyFilter.
    def exitPropertyFilter(self, ctx:PowerEventDSLParser.PropertyFilterContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#propertyName.
    def enterPropertyName(self, ctx:PowerEventDSLParser.PropertyNameContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#propertyName.
    def exitPropertyName(self, ctx:PowerEventDSLParser.PropertyNameContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#timeValue.
    def enterTimeValue(self, ctx:PowerEventDSLParser.TimeValueContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#timeValue.
    def exitTimeValue(self, ctx:PowerEventDSLParser.TimeValueContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#timeUnit.
    def enterTimeUnit(self, ctx:PowerEventDSLParser.TimeUnitContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#timeUnit.
    def exitTimeUnit(self, ctx:PowerEventDSLParser.TimeUnitContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#timeSpec.
    def enterTimeSpec(self, ctx:PowerEventDSLParser.TimeSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#timeSpec.
    def exitTimeSpec(self, ctx:PowerEventDSLParser.TimeSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#timeExpr.
    def enterTimeExpr(self, ctx:PowerEventDSLParser.TimeExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#timeExpr.
    def exitTimeExpr(self, ctx:PowerEventDSLParser.TimeExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#nowExpr.
    def enterNowExpr(self, ctx:PowerEventDSLParser.NowExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#nowExpr.
    def exitNowExpr(self, ctx:PowerEventDSLParser.NowExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#intervalSpec.
    def enterIntervalSpec(self, ctx:PowerEventDSLParser.IntervalSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#intervalSpec.
    def exitIntervalSpec(self, ctx:PowerEventDSLParser.IntervalSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#relativeTimeSpec.
    def enterRelativeTimeSpec(self, ctx:PowerEventDSLParser.RelativeTimeSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#relativeTimeSpec.
    def exitRelativeTimeSpec(self, ctx:PowerEventDSLParser.RelativeTimeSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#relativeTimeExpr.
    def enterRelativeTimeExpr(self, ctx:PowerEventDSLParser.RelativeTimeExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#relativeTimeExpr.
    def exitRelativeTimeExpr(self, ctx:PowerEventDSLParser.RelativeTimeExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#relativeTimeValue.
    def enterRelativeTimeValue(self, ctx:PowerEventDSLParser.RelativeTimeValueContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#relativeTimeValue.
    def exitRelativeTimeValue(self, ctx:PowerEventDSLParser.RelativeTimeValueContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#relativeIntervalSpec.
    def enterRelativeIntervalSpec(self, ctx:PowerEventDSLParser.RelativeIntervalSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#relativeIntervalSpec.
    def exitRelativeIntervalSpec(self, ctx:PowerEventDSLParser.RelativeIntervalSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#lawSpec.
    def enterLawSpec(self, ctx:PowerEventDSLParser.LawSpecContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#lawSpec.
    def exitLawSpec(self, ctx:PowerEventDSLParser.LawSpecContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#dynamicExpression.
    def enterDynamicExpression(self, ctx:PowerEventDSLParser.DynamicExpressionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#dynamicExpression.
    def exitDynamicExpression(self, ctx:PowerEventDSLParser.DynamicExpressionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#expression.
    def enterExpression(self, ctx:PowerEventDSLParser.ExpressionContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#expression.
    def exitExpression(self, ctx:PowerEventDSLParser.ExpressionContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#booleanExpr.
    def enterBooleanExpr(self, ctx:PowerEventDSLParser.BooleanExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#booleanExpr.
    def exitBooleanExpr(self, ctx:PowerEventDSLParser.BooleanExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#booleanTerm.
    def enterBooleanTerm(self, ctx:PowerEventDSLParser.BooleanTermContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#booleanTerm.
    def exitBooleanTerm(self, ctx:PowerEventDSLParser.BooleanTermContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#booleanFactor.
    def enterBooleanFactor(self, ctx:PowerEventDSLParser.BooleanFactorContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#booleanFactor.
    def exitBooleanFactor(self, ctx:PowerEventDSLParser.BooleanFactorContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#booleanAtomic.
    def enterBooleanAtomic(self, ctx:PowerEventDSLParser.BooleanAtomicContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#booleanAtomic.
    def exitBooleanAtomic(self, ctx:PowerEventDSLParser.BooleanAtomicContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#comparisonExpr.
    def enterComparisonExpr(self, ctx:PowerEventDSLParser.ComparisonExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#comparisonExpr.
    def exitComparisonExpr(self, ctx:PowerEventDSLParser.ComparisonExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#arithmeticExpr.
    def enterArithmeticExpr(self, ctx:PowerEventDSLParser.ArithmeticExprContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#arithmeticExpr.
    def exitArithmeticExpr(self, ctx:PowerEventDSLParser.ArithmeticExprContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#term.
    def enterTerm(self, ctx:PowerEventDSLParser.TermContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#term.
    def exitTerm(self, ctx:PowerEventDSLParser.TermContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#factor.
    def enterFactor(self, ctx:PowerEventDSLParser.FactorContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#factor.
    def exitFactor(self, ctx:PowerEventDSLParser.FactorContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#numberWithUnit.
    def enterNumberWithUnit(self, ctx:PowerEventDSLParser.NumberWithUnitContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#numberWithUnit.
    def exitNumberWithUnit(self, ctx:PowerEventDSLParser.NumberWithUnitContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#comparison.
    def enterComparison(self, ctx:PowerEventDSLParser.ComparisonContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#comparison.
    def exitComparison(self, ctx:PowerEventDSLParser.ComparisonContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#booleanLiteral.
    def enterBooleanLiteral(self, ctx:PowerEventDSLParser.BooleanLiteralContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#booleanLiteral.
    def exitBooleanLiteral(self, ctx:PowerEventDSLParser.BooleanLiteralContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#variable.
    def enterVariable(self, ctx:PowerEventDSLParser.VariableContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#variable.
    def exitVariable(self, ctx:PowerEventDSLParser.VariableContext):
        pass


    # Enter a parse tree produced by PowerEventDSLParser#unit.
    def enterUnit(self, ctx:PowerEventDSLParser.UnitContext):
        pass

    # Exit a parse tree produced by PowerEventDSLParser#unit.
    def exitUnit(self, ctx:PowerEventDSLParser.UnitContext):
        pass



del PowerEventDSLParser