/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_PROGRAM_VISITOR_H
#define DSL_PROGRAM_VISITOR_H

#include "../utils/ScenarioHandlerInterface.h"
#include "DSLEvent.h"
#include "DSLFunctionDefinition.h"
#include "Mapping/IFLMapping.h"
#include "Mapping/IIDMMapping.h"
#include "PowerEventDSLBaseVisitor.h"
#include "Scope.h"

#include <stdexcept>

class DSLEngine;

class DSLValidationException : public std::invalid_argument {
    public:
        explicit DSLValidationException(const std::string& message) : std::invalid_argument(message) {}
};

/**
 * A resolved point setGridAction (`set ... to ...`).
 */
struct ResolvedGridTargets {
    std::string attribute;
    std::vector<TargetRef> targets;
    std::vector<double> to_values;
    std::string dsl_text;
};

/**
 * A resolved rampSetGridAction (`set ... from X to Y`, ramp-only).
 */
struct ResolvedRampSetTargets {
    std::string attribute;
    std::vector<TargetRef> targets;
    double from_value = 0.0;
    double to_value = 0.0;
    bool from_is_implicit = false;  // No 'from' written: start from the element's current measured value
    std::string dsl_text;
};

/**
 * A resolved adjustGridAction (`increase/decrease ... by N%`).
 */
struct ResolvedPercentTargets {
    std::string attribute;
    std::vector<TargetRef> targets;
    double percent_delta = 0.0;  // signed, e.g. -5.0 for "decrease by 5%"
    std::string dsl_text;
};

/**
 * Walks a parsed statement/function-call and builds a flat batch of candidate DSLEvents (committed by the DSLEngine itself with DSLEngine::commitBatch
 * after a full successful expansion). Also resolves the "value" rules (stringAtom/numericAtom/booleanAtom/varRef, etc.) used along the way.
 *
 * One visitor instance is used per top-level statement/function call), so scope_ is fixed for that attempt.
 * time_context_ is the absolute time (i.e. when the DSL script is loaded) which new relative offsets are resolved against.
 * exclude_event_id is an optional event id against which ramp-overlap checks should not be performed (used when editing an event via PUT /queue/{id}
 * so that it does not conflicts with itself)
 */
class DSLProgramVisitor : public PowerEventDSLBaseVisitor {
    public:
        DSLProgramVisitor(DSLEngine& engine, ScenarioHandlerInterface& scenario_handler, IIDMMapping& iidm_mapping,
                          IFLMapping& ifl_mapping, double time_context,
                          std::shared_ptr<Scope> scope, std::optional<unsigned long> parent_event_id,
                          std::string source_name, std::optional<unsigned long> exclude_event_id = std::nullopt);

        /**
         * Registers a top-level functionDef's name/params/body text into the engine.
         */
        void registerFunctionDef(PowerEventDSLParser::FunctionDefContext* def_ctx);

        void visitFunctionBody(PowerEventDSLParser::FunctionDefContext* ctx);

        /**
         * Returns the generated batch of DSL events
         */
        std::vector<std::unique_ptr<DSLEvent>>& batch() { return batch_; }

        // Statements
        std::any visitClusterDef(PowerEventDSLParser::ClusterDefContext* ctx) override;
        std::any visitEventDef(PowerEventDSLParser::EventDefContext* ctx) override;
        std::any visitTriggeredStatement(PowerEventDSLParser::TriggeredStatementContext* ctx) override;

        // Executables
        std::any visitSwitchAction(PowerEventDSLParser::SwitchActionContext* ctx) override;
        std::any visitLineAction(PowerEventDSLParser::LineActionContext* ctx) override;
        std::any visitTransformerAction(PowerEventDSLParser::TransformerActionContext* ctx) override;
        std::any visitAdjustGridAction(PowerEventDSLParser::AdjustGridActionContext* ctx) override;
        std::any visitSetGridAction(PowerEventDSLParser::SetGridActionContext* ctx) override;
        std::any visitNetworkAction(PowerEventDSLParser::NetworkActionContext* ctx) override;
        std::any visitCallExpr(PowerEventDSLParser::CallExprContext* ctx) override;
        std::any visitValidateExpr(PowerEventDSLParser::ValidateExprContext* ctx) override;

        // Values
        std::any visitStringAtom(PowerEventDSLParser::StringAtomContext* ctx) override;
        std::any visitNumericAtom(PowerEventDSLParser::NumericAtomContext* ctx) override;
        std::any visitBooleanAtom(PowerEventDSLParser::BooleanAtomContext* ctx) override;
        std::any visitVarRef(PowerEventDSLParser::VarRefContext* ctx) override;
        std::any visitSignedNumericAtom(PowerEventDSLParser::SignedNumericAtomContext* ctx) override;
        std::any visitSignedNumber(PowerEventDSLParser::SignedNumberContext* ctx) override;

        std::vector<std::string> resolveTarget(PowerEventDSLParser::TargetContext* ctx);
        std::vector<std::string> resolveDynamicModelTarget(PowerEventDSLParser::DynamicModelTargetContext* ctx);
        std::vector<std::string> resolveDynamicModelIds(PowerEventDSLParser::DynamicModelListContext* ctx);
        ClusterDef resolveDynamicModelClusterDefinition(PowerEventDSLParser::DynamicModelClusterDefinitionContext* ctx,
                                                         const std::string& model_lib);
        std::string dynamicModelLib(PowerEventDSLParser::DynamicModelTargetContext* ctx);
        double resolveTimeValue(PowerEventDSLParser::TimeValueContext* ctx);
        /**
         * Absolute when the anchor is 'at', an offset from time_context_ when it is 'after' or absent.
         * Rejects 'at' inside a function body, and 'at' a time already past.
         */
        double resolveTimeExpr(PowerEventDSLParser::TimeExprContext* ctx,
                                PowerEventDSLParser::TimeAnchorContext* anchor);
        double resolveTimeValueParts(PowerEventDSLParser::NumericAtomContext* amount_ctx, PowerEventDSLParser::TimeUnitContext* unit_ctx);
        double resolveLikelihood(PowerEventDSLParser::LikelihoodClauseContext* ctx);
        nlohmann::json buildCorruptionFunction(PowerEventDSLParser::CorruptionFunctionContext* ctx);

        ResolvedPercentTargets resolveAdjustGridAction(PowerEventDSLParser::AdjustGridActionContext* ctx);
        ResolvedGridTargets resolveSetGridAction(PowerEventDSLParser::SetGridActionContext* ctx);
        ResolvedRampSetTargets resolveRampSetGridAction(PowerEventDSLParser::RampSetGridActionContext* ctx);

        // Boolean/arithmetic expression tree builders (see DSLExprEval.h) for when/when_rearming guards.
        nlohmann::json buildBoolExpr(PowerEventDSLParser::BooleanExprContext* ctx);
        nlohmann::json buildBoolTerm(PowerEventDSLParser::BooleanTermContext* ctx);
        nlohmann::json buildBoolFactor(PowerEventDSLParser::BooleanFactorContext* ctx);
        nlohmann::json buildBoolAtomic(PowerEventDSLParser::BooleanAtomicContext* ctx);
        nlohmann::json buildComparisonExpr(PowerEventDSLParser::ComparisonExprContext* ctx);
        nlohmann::json buildArithExpr(PowerEventDSLParser::ArithmeticExprContext* ctx);
        nlohmann::json buildTerm(PowerEventDSLParser::TermContext* ctx);
        nlohmann::json buildFactor(PowerEventDSLParser::FactorContext* ctx);
        nlohmann::json buildVariableNode(PowerEventDSLParser::VariableContext* ctx);

        /**
         * Validate a function call without committing anything
         */
        void validateCallExpr(PowerEventDSLParser::CallExprContext* ctx);

        ParamValue resolveCallArgValue(PowerEventDSLParser::CallArgValueContext* ctx);
        /**
         * Match a call's arguments against the callee's parameters and return them in declaration order.
         * Throws DSLValidationException if an argument names no parameter, names one twice, or if too many args are specified
         */
        std::vector<ParamValue> resolveCallArgs(PowerEventDSLParser::CallArgListContext* ctx,
                                                const FunctionDefinition& func_def);

    private:
        unsigned long newEventId();

        /**
         * Validate payload using scenario_handler_.applyScenario(payload, Mode::Validate), and checking for possible overlaps with existing ramps.
         * '[start, end]' is when the DSL engine will apply the payload, the same instant twice for a point action
         * and the whole interval for a ramp. It has to be passed separately because the payload itself carries no
         * time (see assertUntimedPayload() in DSLEvent.h), and only the ramp-overlap check needs to know it.
         * Throws DSLValidationException on failure.
         */
        void validatePayload(const nlohmann::json& payload, double start, double end);

        std::string resolveAttribute(PowerEventDSLParser::InputTypeContext* input_type_ctx);

        // The gridElementType text of a target, regardless of which alternative matched.
        /**
         * How the target reads back in the replay log: the element type for an IIDM target, the quoted model
         * library for a dynamic model.
         */
        std::string targetTypeText(PowerEventDSLParser::TargetContext* ctx);

        /**
         * Return the name of the output a ramp with no 'from' reads its starting value from. Throws if the element publishes none.
         */
        std::string rampStartOutputId(const TargetRef& target, const std::string& attribute);

        ClusterDef resolveClusterDefinition(PowerEventDSLParser::ClusterDefinitionContext* ctx, const std::string& element_type);
        std::vector<std::string> resolveClusterIds(const ClusterDef& def);

        void applyTagIfPresent(PowerEventDSLParser::TaggedContext* tagged_ctx, const std::vector<unsigned long>& created_ids);

        std::string joinIds(const std::vector<std::string>& ids);
        /**
         * How a target reads in DSL: a bare quoted id on its own, a bracketed list when there are several.
         */
        std::string describeTarget(const std::vector<std::string>& ids);

        /**
         * Reconstructs ctx's original source text, for error messages that need to show the offending DSL line.
         */
        std::string sourceTextOf(antlr4::ParserRuleContext* ctx);

        DSLEngine& engine_;
        ScenarioHandlerInterface& scenario_handler_;
        IIDMMapping& iidm_mapping_;
        IFLMapping& ifl_mapping_;
        double time_context_;
        bool in_function_body_ = false;
        std::shared_ptr<Scope> scope_;
        std::optional<unsigned long> parent_event_id_;
        std::string source_name_;
        std::optional<unsigned long> exclude_event_id_;
        std::vector<std::unique_ptr<DSLEvent>> batch_;
};

#endif // DSL_PROGRAM_VISITOR_H
