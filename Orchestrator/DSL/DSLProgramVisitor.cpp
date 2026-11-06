/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLProgramVisitor.h"
#include "../utils/Mode.h"
#include "DSLEngine.h"
#include "Orchestrator.h"

#include <fmt/core.h>

#include <algorithm>
#include <regex>

static std::string describeArithExpr(const nlohmann::json& node) {
    std::string type = node.at("type").get<std::string>();
    if (type == "const") return fmt::format("{}", node.at("value").get<double>());
    // "dsl" is what the user wrote; the bare "id" fallback is for expressions restored from a dump taken
    // before it was recorded, and does not re-parse (no grammar rule matches a bare Dynawo output id).
    if (type == "var") return node.value("dsl", node.at("id").get<std::string>());
    return fmt::format("({} {} {})", describeArithExpr(node.at("left")), node.at("op").get<std::string>(), describeArithExpr(node.at("right")));
}

static std::string describeBoolExpr(const nlohmann::json& node) {
    std::string type = node.at("type").get<std::string>();
    if (type == "bool") return node.at("value").get<bool>() ? "true" : "false";
    if (type == "cmp") return fmt::format("{} {} {}", describeArithExpr(node.at("left")), node.at("op").get<std::string>(), describeArithExpr(node.at("right")));
    std::string joiner = type == "and" ? " and " : " or ";
    std::string result;
    for (auto& operand : node.at("operands")) {
        if (!result.empty()) result += joiner;
        std::string operand_type = operand.value("type", std::string());
        bool is_group = operand_type == "and" || operand_type == "or";
        result += is_group ? "(" + describeBoolExpr(operand) + ")" : describeBoolExpr(operand);
    }
    return result;
}

static std::string describeDelayFunction(const nlohmann::json& fn) {
    if (fn.at("type") == "fixed") return fmt::format("delay fixed {} seconds", fn.at("delay").get<double>());
    return fmt::format("delay gauss mean {} seconds stddev {} seconds", fn.at("mean").get<double>(), fn.at("stddev").get<double>());
}

static std::string describeDropFunction(const nlohmann::json& fn) {
    if (fn.at("type") == "fixed") return fmt::format("drop fixed {}", fn.at("value").get<bool>() ? "true" : "false");
    return fmt::format("drop random {}", fn.at("value").get<double>());
}

static std::string describeCorruptionFunction(const nlohmann::json& fn) {
    std::string type = fn.at("type").get<std::string>();
    std::string likelihood = fn.contains("likelihood") ? fmt::format(" likelihood {}", fn.at("likelihood").get<double>()) : "";
    if (type == "NoCorruption") return "corruption none" + likelihood;
    if (type == "RandomNoiseMeasurementCorruption") {
        return fmt::format("corruption random_noise_measurement{} range {} to {}", likelihood, fn.at("noise_min").get<double>(), fn.at("noise_max").get<double>());
    }
    if (type == "RandomNoiseControlCorruption") {
        return fmt::format("corruption random_noise_control{} range {} to {}", likelihood, fn.at("noise_min").get<double>(), fn.at("noise_max").get<double>());
    }
    if (type == "ZeroOutMeasurementCorruption") {
        return fn.contains("zero_value") ? fmt::format("corruption zero_out_measurement{} value {}", likelihood, fn.at("zero_value").get<double>())
                                          : "corruption zero_out_measurement" + likelihood;
    }
    if (type == "ShiftMeasurementCorruption") return fmt::format("corruption shift_measurement{} by {}", likelihood, fn.at("shift_value").get<double>());
    // InvertControlCorruption
    return fn.contains("invert_factor") ? fmt::format("corruption invert_control{} by {}", likelihood, fn.at("invert_factor").get<double>())
                                         : "corruption invert_control" + likelihood;
}

DSLProgramVisitor::DSLProgramVisitor(DSLEngine& engine, ScenarioHandlerInterface& scenario_handler, IIDMMapping& iidm_mapping,
                                     IFLMapping& ifl_mapping, double time_context,
                                     std::shared_ptr<Scope> scope, std::optional<unsigned long> parent_event_id,
                                     std::string source_name, std::optional<unsigned long> exclude_event_id) :
    engine_(engine),
    scenario_handler_(scenario_handler),
    iidm_mapping_(iidm_mapping),
    ifl_mapping_(ifl_mapping),
    time_context_(time_context),
    scope_(std::move(scope)),
    parent_event_id_(parent_event_id),
    source_name_(std::move(source_name)),
    exclude_event_id_(exclude_event_id) {}

/** Renders a time the way the DSL spells it, so an error quotes back something the user could paste. */
static std::string describeSeconds(double seconds) {
    return fmt::format("{:.6g} seconds", seconds);
}

unsigned long DSLProgramVisitor::newEventId() {
    return engine_.newEventId();
}

/** Wraps resolved ids into the refs IIDMMapping addresses them by. */
static std::vector<TargetRef> targetRefs(const std::vector<std::string>& ids, bool is_dynamic_model) {
    std::vector<TargetRef> refs;
    refs.reserve(ids.size());
    for (auto& id : ids) refs.push_back(TargetRef{id, is_dynamic_model});
    return refs;
}

std::string DSLProgramVisitor::describeTarget(const std::vector<std::string>& ids) {
    return ids.size() == 1 ? "\"" + ids[0] + "\"" : joinIds(ids);
}

std::string DSLProgramVisitor::joinIds(const std::vector<std::string>& ids) {
    std::string joined = "[";
    for (size_t i = 0; i < ids.size(); i++) {
        if (i > 0) joined += ", ";
        joined += "\"" + ids[i] + "\"";
    }
    return joined + "]";
}

std::string DSLProgramVisitor::sourceTextOf(antlr4::ParserRuleContext* ctx) {
    auto* start_token = ctx->getStart();
    auto* stop_token = ctx->getStop();
    antlr4::misc::Interval interval(start_token->getStartIndex(), stop_token->getStopIndex());
    return start_token->getInputStream()->getText(interval);
}

void DSLProgramVisitor::validatePayload(const nlohmann::json& payload, double start, double end) {
    // Priority policy: never allow an action on an (iidm_id, attribute) at a time that
    // overlaps an already-scheduled ramp on that same target.
    std::string command = payload.value("command", std::string());
    if (command == "iidm_command" || command == "scale_multiplier"
        || command == "dynamic_model_command" || command == "dynamic_model_scale_multiplier") {
        // A dynamic model is keyed by its own name where an IIDM element is keyed by its equipment id
        std::string target_id = payload.contains("dynamic_model") ? payload.at("dynamic_model") : payload.at("iidm_id");
        std::string attribute = payload.at("attribute");
        if (engine_.hasActiveRampOn(target_id, attribute, start, end, exclude_event_id_)) {
            throw DSLValidationException("A ramp is already running on " + target_id + "/" + attribute);
        }
    }
    try {
        nlohmann::json reply = scenario_handler_.applyScenario(payload, Mode::Validate);
        std::string status = reply.value("status", std::string("OK"));
        if (status != "OK") {
            throw DSLValidationException(status);
        }
    } catch (const DSLValidationException&) {
        throw;
    } catch (const std::exception& e) {
        throw DSLValidationException(e.what());
    }
}

void DSLProgramVisitor::applyTagIfPresent(PowerEventDSLParser::TaggedContext* tagged_ctx, const std::vector<unsigned long>& created_ids) {
    if (!tagged_ctx) return;
    std::string tag_text = std::any_cast<std::string>(visit(tagged_ctx->tag()->stringAtom()));
    std::string qualifying_prefix = scope_->invocationId() + "/";
    // Strip qualifying prefix is already present (e.g. when editing an existing event)
    std::string bare_tag = tag_text.starts_with(qualifying_prefix) ? tag_text.substr(qualifying_prefix.size()) : tag_text;
    scope_->defineTag(bare_tag);
    std::string qualified_tag = *scope_->resolveTag(bare_tag);
    for (auto& id : created_ids) {
        for (auto& event : batch_) {
            if (event->getId() == id) event->setTag(qualified_tag);
        }
    }
}

void DSLProgramVisitor::registerFunctionDef(PowerEventDSLParser::FunctionDefContext* def_ctx) {
    auto def = std::make_shared<FunctionDefinition>();
    def->name = def_ctx->IDENTIFIER()->getText();
    if (def_ctx->functionParamList()) {
        for (auto* param : def_ctx->functionParamList()->IDENTIFIER()) {
            def->param_names.push_back(param->getText());
        }
    }
    // Raw body text = the source between the function's '{' and '}'.
    auto* start_token = def_ctx->getStart();
    auto* stop_token = def_ctx->getStop();
    antlr4::misc::Interval body_interval(start_token->getStartIndex(), stop_token->getStopIndex());
    std::string full_text = start_token->getInputStream()->getText(body_interval);
    auto open_brace = full_text.find('{');
    auto close_brace = full_text.rfind('}');
    def->body_text = (open_brace != std::string::npos && close_brace != std::string::npos && close_brace > open_brace)
        ? full_text.substr(open_brace + 1, close_brace - open_brace - 1)
        : "";
    engine_.registerFunction(def);
}

void DSLProgramVisitor::visitFunctionBody(PowerEventDSLParser::FunctionDefContext* ctx) {
    in_function_body_ = true;
    // Iterate children in order instead of using ctx->clusterDef() and ctx->eventDef that returns vectors and lose releative order of clusters and events
    for (auto* child : ctx->children) {
        if (auto* cluster = dynamic_cast<PowerEventDSLParser::ClusterDefContext*>(child)) {
            visit(cluster);
        } else if (auto* event = dynamic_cast<PowerEventDSLParser::EventDefContext*>(child)) {
            visit(event);
        }
    }
}

std::any DSLProgramVisitor::visitClusterDef(PowerEventDSLParser::ClusterDefContext* ctx) {
    std::string name = std::any_cast<std::string>(visit(ctx->clusterId()->stringAtom()));
    if (ctx->dynamicModelLibAtom()) {
        std::string model_lib = std::any_cast<std::string>(visit(ctx->dynamicModelLibAtom()->stringAtom()));
        scope_->defineCluster(name, resolveDynamicModelClusterDefinition(ctx->dynamicModelClusterDefinition(), model_lib));
        return {};
    }
    std::string grid_type = ctx->gridElementType()->getText();
    scope_->defineCluster(name, resolveClusterDefinition(ctx->clusterDefinition(), grid_type));
    return {};
}

std::any DSLProgramVisitor::visitEventDef(PowerEventDSLParser::EventDefContext* ctx) {
    if (ctx->triggeredStatement()) {
        return visit(ctx->triggeredStatement());
    }

    try {
        std::vector<unsigned long> created_ids;

        if (ctx->intervalSpec()) {
            auto* interval = ctx->intervalSpec();
            double resolved_time = resolveTimeExpr(interval->timeExpr(0), ctx->timeAnchor());
            double interval_end = resolveTimeExpr(interval->timeExpr(1), ctx->timeAnchor());
            if (interval_end < resolved_time) {
                throw DSLValidationException(fmt::format(
                    "Ramp interval end ({}) is before its start ({})", interval_end, resolved_time));
            }
            auto* rampable = ctx->rampableAction();

            std::vector<RampTarget> ramp_targets;
            RampParameters parameters;
            parameters.interval_start = resolved_time;
            parameters.interval_end = interval_end;
            if (interval->lawSpec()) {
                std::string law_text = interval->lawSpec()->getText();
                if (law_text != "linear") throw DSLValidationException("Unknown ramp law: " + law_text);
                parameters.law = RampLaw::Linear;
            } else {
                parameters.law = RampLaw::Linear;
            }
            std::string dsl_text;

            if (rampable->adjustGridAction()) {
                ResolvedPercentTargets resolved = resolveAdjustGridAction(rampable->adjustGridAction());
                parameters.kind = RampKind::Multiplier;
                for (auto& target : resolved.targets) {
                    // Validates target/attribute exists and that nothing else ramps it over this interval
                    validatePayload(iidm_mapping_.buildScaleMultiplierCommand(target, resolved.attribute, 0.0),
                                    resolved_time, interval_end);
                    RampTarget rt;
                    rt.target = target;
                    rt.attribute = resolved.attribute;
                    rt.total_percent = resolved.percent_delta;
                    ramp_targets.push_back(rt);
                }
                dsl_text = resolved.dsl_text;
            } else {
                ResolvedRampSetTargets resolved = resolveRampSetGridAction(rampable->rampSetGridAction());
                parameters.kind = RampKind::Value;
                for (auto& target : resolved.targets) {
                    // Validates target/attribute exists and that nothing else ramps it over this interval
                    validatePayload(iidm_mapping_.buildSetCommand(target, resolved.attribute, resolved.to_value),
                                    resolved_time, interval_end);
                    RampTarget rt;
                    rt.target = target;
                    rt.attribute = resolved.attribute;
                    rt.from_value = resolved.from_value;
                    rt.to_value = resolved.to_value;
                    if (resolved.from_is_implicit) {
                        rt.start_output_id = rampStartOutputId(target, resolved.attribute);
                        rt.start_resolved = false;
                    }
                    ramp_targets.push_back(rt);
                }
                dsl_text = resolved.dsl_text;
            }

            for (auto& target : ramp_targets) {
                engine_.registerPendingRamp(target.target.id, target.attribute, resolved_time, interval_end);
            }

            unsigned long id = newEventId();
            auto ramp = std::make_unique<RampEvent>(id, dsl_text, time_context_, source_name_, parent_event_id_,
                                                                           ramp_targets, parameters);
            created_ids.push_back(id);
            batch_.push_back(std::move(ramp));
        } else {
            double resolved_time = ctx->timeExpr() ? resolveTimeExpr(ctx->timeExpr(), ctx->timeAnchor()) : time_context_;
            auto* exec = ctx->executable();

            // Mutate time_context_ before entering visit, so that, e.g. at 30s, callFunc() has its internals relative to the time of the function call
            double saved_time_context = time_context_;
            time_context_ = resolved_time;
            std::any result;
            try {
                result = visit(exec);
            } catch (...) {
                // Revert the time_context_ edit
                time_context_ = saved_time_context;
                throw;
            }
            // Revert the time_context_ edit
            time_context_ = saved_time_context;
            if (result.has_value()) {
                try {
                    created_ids = std::any_cast<std::vector<unsigned long>>(result);
                } catch (const std::bad_any_cast&) {}
            }
        }

        applyTagIfPresent(ctx->tagged(), created_ids);
        return created_ids;
    } catch (const std::exception& e) {
        throw DSLValidationException(fmt::format("{} (line {}: \"{}\")", e.what(),
                                                   ctx->getStart()->getLine(), sourceTextOf(ctx)));
    }
}

std::any DSLProgramVisitor::visitTriggeredStatement(PowerEventDSLParser::TriggeredStatementContext* ctx) {
    try {
        std::string keyword = ctx->children[0]->getText();
        TriggerKind kind = keyword == "when" ? TriggerKind::When
                          : keyword == "when_rearming" ? TriggerKind::WhenRearming
                          : TriggerKind::After;

        nlohmann::json condition_expr;
        std::optional<std::string> dependency_tag;
        switch (kind) {
            case TriggerKind::After: {
                std::string bare_tag = std::any_cast<std::string>(visit(ctx->tag()->stringAtom()));
                auto qualified = scope_->resolveTag(bare_tag);
                if (!qualified) throw DSLValidationException("Unknown tag: " + bare_tag);
                dependency_tag = qualified;
                break;
            }
            case TriggerKind::When:
            case TriggerKind::WhenRearming:
                condition_expr = buildBoolExpr(ctx->dynamicExpression()->expression()->booleanExpr());
                break;
        }

        std::vector<nlohmann::json> action_payloads;
        std::string action_call_source;
        std::string body_text;

        if (auto* call = ctx->executable()->callExpr()) {
            // Function call: store the call itself, and expend it when triggered
            auto* start_token = call->getStart();
            auto* stop_token = call->getStop();
            action_call_source = start_token->getInputStream()->getText(
                antlr4::misc::Interval(start_token->getStartIndex(), stop_token->getStopIndex()));
            body_text = action_call_source;

            // Validate function call now instead of when triggered
            validateCallExpr(call);
        } else {
            // Simple event: simply store its payloads
            auto batch_size_before = batch_.size();
            visit(ctx->executable());
            if (batch_.size() != batch_size_before + 1) {
                throw DSLValidationException("when/when_rearming/after body must resolve to exactly one action");
            }
            auto action_event = std::move(batch_.back());
            batch_.pop_back();
            auto* as_action = dynamic_cast<ActionEvent*>(action_event.get());
            if (!as_action) {
                throw DSLValidationException("when/when_rearming/after body must be an immediate (non-ramped) action");
            }
            action_payloads = as_action->getPayloads();
            body_text = as_action->getDslText();
        }

        unsigned long id = newEventId();
        std::string dsl_text;
        switch (kind) {
            case TriggerKind::After:
                dsl_text = fmt::format("after \"{}\" is completed, {}", *dependency_tag, body_text);
                break;
            case TriggerKind::When:
                dsl_text = fmt::format("when {}, {}", describeBoolExpr(condition_expr), body_text);
                break;
            case TriggerKind::WhenRearming:
                dsl_text = fmt::format("when_rearming {}, {}", describeBoolExpr(condition_expr), body_text);
                break;
        }
        auto cond = std::make_unique<ConditionalEvent>(id, dsl_text, time_context_, source_name_, parent_event_id_,
                                                        kind, condition_expr, std::move(action_payloads), dependency_tag,
                                                        std::move(action_call_source));

        std::vector<unsigned long> created_ids{id};
        batch_.push_back(std::move(cond));
        applyTagIfPresent(ctx->tagged(), created_ids);
        return created_ids;
    } catch (const std::exception& e) {
        throw DSLValidationException(fmt::format("{} (line {}: \"{}\")", e.what(), ctx->getStart()->getLine(), sourceTextOf(ctx)));
    }
}

std::any DSLProgramVisitor::visitSwitchAction(PowerEventDSLParser::SwitchActionContext* ctx) {
    std::string operation = ctx->children[0]->getText();
    std::string switch_id = std::any_cast<std::string>(visit(ctx->switchId()->stringAtom()));
    double value = iidm_mapping_.resolveStateValue("switch", operation);
    nlohmann::json payload = iidm_mapping_.buildSetCommand(TargetRef{switch_id}, "state", value);
    validatePayload(payload, time_context_, time_context_);

    unsigned long id = newEventId();
    std::string dsl_text = fmt::format("{} switch \"{}\"", operation, switch_id);
    batch_.push_back(std::make_unique<ActionEvent>(id, dsl_text, time_context_, source_name_, parent_event_id_,
                                                     time_context_, payload));
    return std::vector<unsigned long>{id};
}

std::any DSLProgramVisitor::visitLineAction(PowerEventDSLParser::LineActionContext* ctx) {
    std::string operation = ctx->children[0]->getText();
    std::string line_id = std::any_cast<std::string>(visit(ctx->lineId()->stringAtom()));
    double value = iidm_mapping_.resolveStateValue("line", operation);
    nlohmann::json payload = iidm_mapping_.buildSetCommand(TargetRef{line_id}, "state", value);
    validatePayload(payload, time_context_, time_context_);

    unsigned long id = newEventId();
    std::string dsl_text = fmt::format("{} line \"{}\"", operation, line_id);
    batch_.push_back(std::make_unique<ActionEvent>(id, dsl_text, time_context_, source_name_, parent_event_id_,
                                                     time_context_, payload));
    return std::vector<unsigned long>{id};
}

std::any DSLProgramVisitor::visitTransformerAction(PowerEventDSLParser::TransformerActionContext* ctx) {
    std::string operation = ctx->children[0]->getText();
    std::string transformer_id = std::any_cast<std::string>(visit(ctx->transformerId()->stringAtom()));
    double value = iidm_mapping_.resolveStateValue("transformer", operation);
    nlohmann::json payload = iidm_mapping_.buildSetCommand(TargetRef{transformer_id}, "state", value);
    validatePayload(payload, time_context_, time_context_);

    unsigned long id = newEventId();
    std::string dsl_text = fmt::format("{} transformer \"{}\"", operation, transformer_id);
    batch_.push_back(std::make_unique<ActionEvent>(id, dsl_text, time_context_, source_name_, parent_event_id_,
                                                     time_context_, payload));
    return std::vector<unsigned long>{id};
}

std::string DSLProgramVisitor::resolveAttribute(PowerEventDSLParser::InputTypeContext* input_type_ctx) {
    return std::any_cast<std::string>(visit(input_type_ctx->stringAtom()));
}

ResolvedPercentTargets DSLProgramVisitor::resolveAdjustGridAction(PowerEventDSLParser::AdjustGridActionContext* ctx) {
    std::string operation = ctx->children[0]->getText();
    std::string grid_type = targetTypeText(ctx->target());
    auto ids = resolveTarget(ctx->target());
    bool is_dynamic_model = ctx->target()->dynamicModelTarget() != nullptr;
    std::string attribute = resolveAttribute(ctx->inputType());
    double percent = std::any_cast<double>(visit(ctx->numericAtom()));
    double sign = (operation == "increase") ? 1.0 : -1.0;

    ResolvedPercentTargets result;
    result.attribute = attribute;
    result.targets = targetRefs(ids, is_dynamic_model);
    result.percent_delta = sign * percent;
    // Negative ramp of more than 100% could cause a div by 0 of the multiplier in a ramp
    if (result.percent_delta < -100.0) {
        throw DSLValidationException(fmt::format("{} by {}% would take the input multiplier below zero, a decrease is limited to 100%", operation, percent));
    }
    result.dsl_text = fmt::format("{} {} {} input \"{}\" by {}%", operation, grid_type, describeTarget(ids), attribute, percent);
    return result;
}

ResolvedGridTargets DSLProgramVisitor::resolveSetGridAction(PowerEventDSLParser::SetGridActionContext* ctx) {
    std::string grid_type = targetTypeText(ctx->target());
    auto ids = resolveTarget(ctx->target());
    bool is_dynamic_model = ctx->target()->dynamicModelTarget() != nullptr;
    std::string attribute = resolveAttribute(ctx->inputType());
    double to_value = std::any_cast<double>(visit(ctx->signedNumber()));

    ResolvedGridTargets result;
    result.attribute = attribute;
    result.targets = targetRefs(ids, is_dynamic_model);
    result.to_values.assign(ids.size(), to_value);
    result.dsl_text = fmt::format("set {} {} input \"{}\" to {}", grid_type, describeTarget(ids), attribute, to_value);
    return result;
}

ResolvedRampSetTargets DSLProgramVisitor::resolveRampSetGridAction(PowerEventDSLParser::RampSetGridActionContext* ctx) {
    std::string grid_type = targetTypeText(ctx->target());
    auto ids = resolveTarget(ctx->target());
    bool is_dynamic_model = ctx->target()->dynamicModelTarget() != nullptr;
    std::string attribute = resolveAttribute(ctx->inputType());
    bool has_from = ctx->signedNumber().size() == 2;
    double from_value = has_from ? std::any_cast<double>(visit(ctx->signedNumber(0))) : 0.0;
    double to_value = std::any_cast<double>(visit(ctx->signedNumber(has_from ? 1 : 0)));

    ResolvedRampSetTargets result;
    result.attribute = attribute;
    result.targets = targetRefs(ids, is_dynamic_model);
    result.from_value = from_value;
    result.to_value = to_value;
    result.from_is_implicit = !has_from;
    result.dsl_text = has_from
        ? fmt::format("set {} {} input \"{}\" from {} to {}", grid_type, describeTarget(ids), attribute, from_value, to_value)
        : fmt::format("set {} {} input \"{}\" to {}", grid_type, describeTarget(ids), attribute, to_value);
    return result;
}

std::any DSLProgramVisitor::visitAdjustGridAction(PowerEventDSLParser::AdjustGridActionContext* ctx) {
    auto resolved = resolveAdjustGridAction(ctx);
    std::vector<unsigned long> created_ids;
    std::vector<nlohmann::json> payloads;
    for (auto& target : resolved.targets) {
        payloads.push_back(iidm_mapping_.buildScaleMultiplierCommand(target, resolved.attribute,
                                                                       resolved.percent_delta / 100.0));
        validatePayload(payloads.back(), time_context_, time_context_);
    }
    unsigned long id = newEventId();
    batch_.push_back(std::make_unique<ActionEvent>(id, resolved.dsl_text, time_context_, source_name_,
                                                     parent_event_id_, time_context_, std::move(payloads)));
    created_ids.push_back(id);
    return created_ids;
}

std::any DSLProgramVisitor::visitSetGridAction(PowerEventDSLParser::SetGridActionContext* ctx) {
    auto resolved = resolveSetGridAction(ctx);
    std::vector<unsigned long> created_ids;
    std::vector<nlohmann::json> payloads;
    for (size_t i = 0; i < resolved.targets.size(); i++) {
        payloads.push_back(iidm_mapping_.buildSetCommand(resolved.targets[i], resolved.attribute,
                                                            resolved.to_values[i]));
        validatePayload(payloads.back(), time_context_, time_context_);
    }
    unsigned long id = newEventId();
    batch_.push_back(std::make_unique<ActionEvent>(id, resolved.dsl_text, time_context_, source_name_,
                                                     parent_event_id_, time_context_, std::move(payloads)));
    created_ids.push_back(id);
    return created_ids;
}

std::any DSLProgramVisitor::visitNetworkAction(PowerEventDSLParser::NetworkActionContext* ctx) {
    std::vector<std::string> nodes;
    std::vector<std::pair<std::string, std::string>> links;

    if (ctx->linkStatement()) {
        for (auto* link_ctx : ctx->linkStatement()->linkClause()) {
            auto ids = link_ctx->nodeId();
            std::string from = std::any_cast<std::string>(visit(ids[0]->stringAtom()));
            std::string to = std::any_cast<std::string>(visit(ids[1]->stringAtom()));
            links.push_back({from, to});
        }
    }
    if (ctx->nodeStatement()) {
        for (auto* node_ctx : ctx->nodeStatement()->nodeClause()) {
            nodes.push_back(std::any_cast<std::string>(visit(node_ctx->nodeId()->stringAtom())));
        }
    }

    nlohmann::json characteristics;
    for (auto* adj : ctx->networkAdjustmentClause()) {
        if (adj->delayClause()) {
            auto* fn = adj->delayClause()->delayFunction();
            std::string head = fn->children[0]->getText();
            auto numeric = fn->numericAtom();
            auto units = fn->timeUnit();
            if (head == "fixed") {
                double delay = resolveTimeValueParts(numeric[0], units[0]);
                characteristics["delay_function"] = {{"type", "fixed"}, {"delay", delay}};
            } else {  // gauss
                double mean = resolveTimeValueParts(numeric[0], units[0]);
                double stddev = resolveTimeValueParts(numeric[1], units[1]);
                characteristics["delay_function"] = {{"type", "gauss"}, {"mean", mean}, {"stddev", stddev}};
            }
        } else if (adj->dropClause()) {
            auto* fn = adj->dropClause()->dropFunction();
            std::string head = fn->children[0]->getText();
            if (head == "fixed") {
                bool value = std::any_cast<bool>(visit(fn->booleanAtom()));
                characteristics["drop_function"] = {{"type", "fixed"}, {"value", value}};
            } else {  // random
                double probability = std::any_cast<double>(visit(fn->numericAtom()));
                characteristics["drop_function"] = {{"type", "random"}, {"value", probability}};
            }
        } else if (adj->corruptionClause()) {
            characteristics["corruption_functions"].push_back(buildCorruptionFunction(adj->corruptionClause()->corruptionFunction()));
        }
    }

    nlohmann::json payload = ifl_mapping_.buildNetworkCharacteristicsCommand(nodes, links, characteristics);
    validatePayload(payload, time_context_, time_context_);

    // Build the dsl_text string with resolved references
    std::vector<std::string> clauses;
    for (auto& [from, to] : links) clauses.push_back(fmt::format("link from \"{}\" to \"{}\"", from, to));
    for (auto& node : nodes) clauses.push_back(fmt::format("node \"{}\"", node));
    if (characteristics.contains("delay_function")) clauses.push_back(describeDelayFunction(characteristics.at("delay_function")));
    if (characteristics.contains("drop_function")) clauses.push_back(describeDropFunction(characteristics.at("drop_function")));
    if (characteristics.contains("corruption_functions")) {
        for (auto& fn : characteristics.at("corruption_functions")) clauses.push_back(describeCorruptionFunction(fn));
    }
    std::string joined_clauses;
    for (size_t i = 0; i < clauses.size(); i++) {
        if (i > 0) joined_clauses += ", ";
        joined_clauses += clauses[i];
    }

    unsigned long id = newEventId();
    std::string dsl_text = fmt::format("change network characteristics {}", joined_clauses);
    batch_.push_back(std::make_unique<ActionEvent>(id, dsl_text, time_context_, source_name_, parent_event_id_,
                                                     time_context_, payload));
    return std::vector<unsigned long>{id};
}

double DSLProgramVisitor::resolveTimeValueParts(PowerEventDSLParser::NumericAtomContext* amount_ctx, PowerEventDSLParser::TimeUnitContext* unit_ctx) {
    double amount = std::any_cast<double>(visit(amount_ctx));
    std::string unit = unit_ctx->getText();
    if (unit == "seconds" || unit == "second" || unit == "s") return amount;
    if (unit == "minutes" || unit == "minute" || unit == "min") return amount * 60.0;
    if (unit == "hours" || unit == "hour" || unit == "h") return amount * 3600.0;
    throw DSLValidationException("Unknown time unit: " + unit);
}

double DSLProgramVisitor::resolveLikelihood(PowerEventDSLParser::LikelihoodClauseContext* ctx) {
    return std::any_cast<double>(visit(ctx->numericAtom()));
}

nlohmann::json DSLProgramVisitor::buildCorruptionFunction(PowerEventDSLParser::CorruptionFunctionContext* ctx) {
    std::string head = ctx->children[0]->getText();
    nlohmann::json result;
    if (head == "none") {
        result = {{"type", "NoCorruption"}, {"likelihood", ctx->likelihoodClause() ? resolveLikelihood(ctx->likelihoodClause()) : 1.0}};
    } else if (head == "random_noise_measurement" || head == "random_noise_control") {
        auto* params = ctx->corruptionNoiseParams();
        double noise_min = std::any_cast<double>(visit(params->numericAtom(0)));
        double noise_max = std::any_cast<double>(visit(params->numericAtom(1)));
        result = {
            {"type", head == "random_noise_measurement" ? "RandomNoiseMeasurementCorruption" : "RandomNoiseControlCorruption"},
            {"noise_min", noise_min}, {"noise_max", noise_max},
        };
        if (params->likelihoodClause()) result["likelihood"] = resolveLikelihood(params->likelihoodClause());
    } else if (head == "zero_out_measurement") {
        auto* params = ctx->corruptionZeroParams();
        result = {{"type", "ZeroOutMeasurementCorruption"}};
        if (params->likelihoodClause()) result["likelihood"] = resolveLikelihood(params->likelihoodClause());
        if (params->numericAtom()) result["zero_value"] = std::any_cast<double>(visit(params->numericAtom()));
    } else if (head == "shift_measurement") {
        auto* params = ctx->corruptionShiftParams();
        result = {{"type", "ShiftMeasurementCorruption"}, {"shift_value", std::any_cast<double>(visit(params->numericAtom()))}};
        if (params->likelihoodClause()) result["likelihood"] = resolveLikelihood(params->likelihoodClause());
    } else { // invert_control
        auto* params = ctx->corruptionInvertParams();
        result = {{"type", "InvertControlCorruption"}};
        if (params->likelihoodClause()) result["likelihood"] = resolveLikelihood(params->likelihoodClause());
        if (params->numericAtom()) result["invert_factor"] = std::any_cast<double>(visit(params->numericAtom()));
    }
    return result;
}

std::any DSLProgramVisitor::visitCallExpr(PowerEventDSLParser::CallExprContext* ctx) {
    std::string func_name = ctx->IDENTIFIER()->getText();
    auto func_def = engine_.lookupFunction(func_name);
    if (!func_def) throw DSLValidationException("Unknown function: " + func_name);

    std::vector<ParamValue> ordered_args = resolveCallArgs(ctx->callArgList(), *func_def);

    unsigned long call_id = newEventId();
    auto expansion = engine_.expandFunctionCall(func_name, ordered_args, time_context_, scope_, call_id, source_name_);

    std::vector<unsigned long> child_ids;
    for (auto& ev : expansion) child_ids.push_back(ev->getId());
    auto* start_token = ctx->getStart();
    auto* stop_token = ctx->getStop();
    std::string dsl_text = start_token->getInputStream()->getText(antlr4::misc::Interval(start_token->getStartIndex(), stop_token->getStopIndex()));
    auto call_event = std::make_unique<FunctionCallEvent>(call_id, dsl_text, time_context_, source_name_,
                                                            parent_event_id_, child_ids);
    for (auto& ev : expansion) batch_.push_back(std::move(ev));
    batch_.push_back(std::move(call_event));
    return std::vector<unsigned long>{call_id};
}

void DSLProgramVisitor::validateCallExpr(PowerEventDSLParser::CallExprContext* ctx) {
    std::string func_name = ctx->IDENTIFIER()->getText();
    auto func_def = engine_.lookupFunction(func_name);
    if (!func_def) throw DSLValidationException("Unknown function: " + func_name);

    std::vector<ParamValue> ordered_args = resolveCallArgs(ctx->callArgList(), *func_def);

    unsigned long scratch_id = newEventId();
    // Validation: expandFunctionCall throws on the first failure and never commits anything.
    engine_.expandFunctionCall(func_name, ordered_args, time_context_, scope_, scratch_id, source_name_);
}

std::any DSLProgramVisitor::visitValidateExpr(PowerEventDSLParser::ValidateExprContext* ctx) {
    validateCallExpr(ctx->callExpr());
    return std::vector<unsigned long>{};
}

std::any DSLProgramVisitor::visitStringAtom(PowerEventDSLParser::StringAtomContext* ctx) {
    if (ctx->STRING()) {
        std::string text = ctx->STRING()->getText();
        return text.substr(1, text.size() - 2);
    }
    auto value = std::any_cast<ParamValue>(visit(ctx->varRef()));
    if (auto* s = std::get_if<std::string>(&value)) return *s;
    throw DSLValidationException("Expected a string-valued parameter for $" + ctx->varRef()->IDENTIFIER()->getText());
}

std::any DSLProgramVisitor::visitNumericAtom(PowerEventDSLParser::NumericAtomContext* ctx) {
    if (ctx->NUMBER()) {
        return std::stod(ctx->NUMBER()->getText());
    }
    auto value = std::any_cast<ParamValue>(visit(ctx->varRef()));
    if (auto* d = std::get_if<double>(&value)) return *d;
    throw DSLValidationException("Expected a numeric-valued parameter for $" + ctx->varRef()->IDENTIFIER()->getText());
}

std::any DSLProgramVisitor::visitBooleanAtom(PowerEventDSLParser::BooleanAtomContext* ctx) {
    if (ctx->booleanLiteral()) {
        return ctx->booleanLiteral()->getText() == "true";
    }
    auto value = std::any_cast<ParamValue>(visit(ctx->varRef()));
    if (auto* b = std::get_if<bool>(&value)) return *b;
    throw DSLValidationException("Expected a boolean-valued parameter for $" + ctx->varRef()->IDENTIFIER()->getText());
}

std::any DSLProgramVisitor::visitVarRef(PowerEventDSLParser::VarRefContext* ctx) {
    std::string name = ctx->IDENTIFIER()->getText();
    auto value = scope_->resolveParamLocalOnly(name);
    if (!value) throw DSLValidationException("Unknown parameter: $" + name);
    return *value;
}

std::any DSLProgramVisitor::visitSignedNumericAtom(PowerEventDSLParser::SignedNumericAtomContext* ctx) {
    double value = std::any_cast<double>(visit(ctx->numericAtom()));
    if (ctx->children.size() > 1 && ctx->children[0]->getText() == "-") value = -value;
    return value;
}

std::any DSLProgramVisitor::visitSignedNumber(PowerEventDSLParser::SignedNumberContext* ctx) {
    return visit(ctx->signedNumericAtom());
}

std::vector<std::string> DSLProgramVisitor::resolveTarget(PowerEventDSLParser::TargetContext* ctx) {
    if (ctx->dynamicModelTarget()) {
        return resolveDynamicModelTarget(ctx->dynamicModelTarget());
    }
    if (ctx->gridElementId()) {
        return {std::any_cast<std::string>(visit(ctx->gridElementId()->stringAtom()))};
    }
    if (ctx->gridElementList()) {
        std::vector<std::string> ids;
        for (auto* elem : ctx->gridElementList()->gridElementId()) {
            ids.push_back(std::any_cast<std::string>(visit(elem->stringAtom())));
        }
        return ids;
    }
    auto* cs = ctx->clusterSpec();
    std::string grid_type = cs->gridElementType()->getText();
    if (cs->clusterDefinition()) {
        ClusterDef def = resolveClusterDefinition(cs->clusterDefinition(), grid_type);
        auto ids = resolveClusterIds(def);
        if (cs->clusterId()) {
            std::string cluster_id = std::any_cast<std::string>(visit(cs->clusterId()->stringAtom()));
            scope_->defineCluster(cluster_id, ClusterDef{grid_type, ids});
        }
        return ids;
    }
    std::string cluster_id = std::any_cast<std::string>(visit(cs->clusterId()->stringAtom()));
    auto def = scope_->resolveCluster(cluster_id);
    if (!def) throw DSLValidationException("Unknown cluster: " + cluster_id);
    auto ids = resolveClusterIds(*def);
    // Freeze a regex-based definition into its resolved ids on first use, i.e. only in the scope that defines it.
    if (std::holds_alternative<ClusterRegexDef>(def->definition) && scope_->definesCluster(cluster_id)) {
        scope_->defineCluster(cluster_id, ClusterDef{def->element_type, ids});
    }
    return ids;
}

std::string DSLProgramVisitor::dynamicModelLib(PowerEventDSLParser::DynamicModelTargetContext* ctx) {
    auto* lib_ctx = ctx->dynamicModelLibAtom() ? ctx->dynamicModelLibAtom()
                                               : ctx->dynamicModelClusterSpec()->dynamicModelLibAtom();
    return std::any_cast<std::string>(visit(lib_ctx->stringAtom()));
}

std::vector<std::string> DSLProgramVisitor::resolveDynamicModelIds(PowerEventDSLParser::DynamicModelListContext* ctx) {
    std::vector<std::string> ids;
    for (auto* model : ctx->dynamicModelAtom()) {
        ids.push_back(std::any_cast<std::string>(visit(model->stringAtom())));
    }
    return ids;
}

std::vector<std::string> DSLProgramVisitor::resolveDynamicModelTarget(PowerEventDSLParser::DynamicModelTargetContext* ctx) {
    if (ctx->dynamicModelAtom()) {
        return {std::any_cast<std::string>(visit(ctx->dynamicModelAtom()->stringAtom()))};
    }
    if (ctx->dynamicModelList()) {
        return resolveDynamicModelIds(ctx->dynamicModelList());
    }

    auto* cs = ctx->dynamicModelClusterSpec();
    std::string model_lib = std::any_cast<std::string>(visit(cs->dynamicModelLibAtom()->stringAtom()));
    if (cs->dynamicModelClusterDefinition()) {
        ClusterDef def = resolveDynamicModelClusterDefinition(cs->dynamicModelClusterDefinition(), model_lib);
        auto ids = resolveClusterIds(def);
        if (cs->clusterId()) {
            std::string cluster_id = std::any_cast<std::string>(visit(cs->clusterId()->stringAtom()));
            scope_->defineCluster(cluster_id, ClusterDef{model_lib, ids, true});
        }
        return ids;
    }

    std::string cluster_id = std::any_cast<std::string>(visit(cs->clusterId()->stringAtom()));
    auto def = scope_->resolveCluster(cluster_id);
    if (!def) throw DSLValidationException("Unknown cluster: " + cluster_id);
    if (!def->is_dynamic_model) {
        throw DSLValidationException("Cluster \"" + cluster_id + "\" holds " + def->element_type
                                      + " elements, so it cannot be used as a dynamic model target");
    }
    auto ids = resolveClusterIds(*def);
    // Freeze a regex-based definition into its resolved ids on first use, as the IIDM form does
    if (std::holds_alternative<ClusterRegexDef>(def->definition) && scope_->definesCluster(cluster_id)) {
        scope_->defineCluster(cluster_id, ClusterDef{def->element_type, ids, true});
    }
    return ids;
}

ClusterDef DSLProgramVisitor::resolveDynamicModelClusterDefinition(PowerEventDSLParser::DynamicModelClusterDefinitionContext* ctx,
                                                                    const std::string& model_lib) {
    if (ctx->dynamicModelList()) {
        return ClusterDef{model_lib, resolveDynamicModelIds(ctx->dynamicModelList()), true};
    }
    auto* regex_ctx = ctx->dynamicModelRegexFilter();
    std::string pattern = std::any_cast<std::string>(visit(regex_ctx->stringAtom()));
    std::string regex_model_lib = std::any_cast<std::string>(visit(regex_ctx->dynamicModelLibAtom()->stringAtom()));
    return ClusterDef{model_lib, ClusterRegexDef{regex_model_lib, pattern, true}, true};
}

std::string DSLProgramVisitor::rampStartOutputId(const TargetRef& target, const std::string& attribute) {
    try {
        return target.is_dynamic_model ? engine_.getDynamicModelOutputId(target.id, attribute)
                                        : engine_.getOutputId(target.id, attribute);
    } catch (const std::exception& e) {
        // Checked here rather than at the first tick, so a ramp that could never start is refused at load
        throw DSLValidationException(fmt::format(
            "without 'from', the ramp starts from the element's current value, which needs a measurement: {}",
            e.what()));
    }
}

std::string DSLProgramVisitor::targetTypeText(PowerEventDSLParser::TargetContext* ctx) {
    if (ctx->dynamicModelTarget()) {
        return fmt::format("\"{}\"", dynamicModelLib(ctx->dynamicModelTarget()));
    }
    if (ctx->gridElementType()) return ctx->gridElementType()->getText();
    return ctx->clusterSpec()->gridElementType()->getText();
}

ClusterDef DSLProgramVisitor::resolveClusterDefinition(PowerEventDSLParser::ClusterDefinitionContext* ctx, const std::string& element_type) {
    if (ctx->gridElementList()) {
        std::vector<std::string> element_ids;
        for (auto* elem : ctx->gridElementList()->gridElementId()) {
            element_ids.push_back(std::any_cast<std::string>(visit(elem->stringAtom())));
        }
        return ClusterDef{element_type, element_ids};
    }

    auto* regex_ctx = ctx->relationshipSpec()->regexFilter();
    if (!regex_ctx) {
        throw DSLValidationException("Only regex-based cluster definitions are currently supported");
    }
    std::string pattern = std::any_cast<std::string>(visit(regex_ctx->stringAtom()));
    std::string regex_grid_type = regex_ctx->gridElementType()->getText();
    return ClusterDef{element_type, ClusterRegexDef{regex_grid_type, pattern}};
}

std::vector<std::string> DSLProgramVisitor::resolveClusterIds(const ClusterDef& def) {
    if (auto* ids = std::get_if<std::vector<std::string>>(&def.definition)) {
        return *ids;
    }
    const auto& regex_def = std::get<ClusterRegexDef>(def.definition);

    std::vector<std::string> all_ids;
    try {
        all_ids = regex_def.is_dynamic_model ? engine_.listDynamicModelIds(regex_def.element_type)
                                              : engine_.listIidmIds(regex_def.element_type);
    } catch (const std::exception& e) {
        throw DSLValidationException(e.what());
    }

    std::regex compiled;
    try {
        compiled = std::regex(regex_def.pattern);
    } catch (const std::regex_error& e) {
        throw DSLValidationException("Invalid regex \"" + regex_def.pattern + "\": " + e.what());
    }

    std::vector<std::string> matched;
    for (auto& id : all_ids) {
        if (std::regex_search(id, compiled)) matched.push_back(id);
    }
    return matched;
}

double DSLProgramVisitor::resolveTimeValue(PowerEventDSLParser::TimeValueContext* ctx) {
    return resolveTimeValueParts(ctx->numericAtom(), ctx->timeUnit());
}

double DSLProgramVisitor::resolveTimeExpr(PowerEventDSLParser::TimeExprContext* ctx, PowerEventDSLParser::TimeAnchorContext* anchor) {
    double offset;
    if (ctx->timeValue()) {
        offset = resolveTimeValue(ctx->timeValue());
    } else {
        auto value = std::any_cast<ParamValue>(visit(ctx->varRef()));
        auto* d = std::get_if<double>(&value);
        if (!d) throw DSLValidationException("Expected a numeric time parameter for $" + ctx->varRef()->IDENTIFIER()->getText());
        offset = *d;
    }

    if (!anchor || anchor->getText() != "at") return time_context_ + offset;

    if (in_function_body_) {
        throw DSLValidationException(fmt::format(
            "'at {0}' is an absolute time, which a function body cannot use, use 'after' instead", describeSeconds(offset)));
    }
    double now = Orchestrator::get().getCurrentTime();
    if (offset < now) {
        throw DSLValidationException(fmt::format(
            "'at {}' is in the past, the simulation is already at {} seconds; use 'after' for a time relative to now",
            describeSeconds(offset), now));
    }
    return offset;
}

std::vector<ParamValue> DSLProgramVisitor::resolveCallArgs(
        PowerEventDSLParser::CallArgListContext* ctx, const FunctionDefinition& func_def) {
    std::unordered_map<std::string, ParamValue> bound;
    std::vector<ParamValue> positional;
    if (ctx) {
        for (auto* arg : ctx->callArg()) {
            ParamValue value = resolveCallArgValue(arg->callArgValue());
            if (!arg->IDENTIFIER()) {
                positional.push_back(std::move(value));
                continue;
            }
            std::string name = arg->IDENTIFIER()->getText();
            if (std::find(func_def.param_names.begin(), func_def.param_names.end(), name) == func_def.param_names.end()) {
                throw DSLValidationException(func_def.name + " has no parameter named " + name);
            }
            if (!bound.emplace(name, std::move(value)).second) {
                throw DSLValidationException(func_def.name + ": argument " + name + " given twice");
            }
        }
    }

    size_t pos_idx = 0;
    std::vector<ParamValue> ordered_args;
    for (auto& param_name : func_def.param_names) {
        if (bound.contains(param_name)) {
            ordered_args.push_back(bound.at(param_name));
        } else if (pos_idx < positional.size()) {
            ordered_args.push_back(positional[pos_idx++]);
        } else {
            throw DSLValidationException("Missing argument for parameter: " + param_name);
        }
    }
    if (pos_idx < positional.size()) {
        throw DSLValidationException(fmt::format("{}: expected {} argument(s), got {}", func_def.name,
            func_def.param_names.size(), bound.size() + positional.size()));
    }
    return ordered_args;
}

ParamValue DSLProgramVisitor::resolveCallArgValue(PowerEventDSLParser::CallArgValueContext* ctx) {
    if (ctx->timeValue()) return resolveTimeValue(ctx->timeValue());
    if (ctx->varRef()) return std::any_cast<ParamValue>(visit(ctx->varRef()));
    if (ctx->signedNumericAtom()) return std::any_cast<double>(visit(ctx->signedNumericAtom()));
    if (ctx->booleanAtom()) return std::any_cast<bool>(visit(ctx->booleanAtom()));
    if (ctx->STRING()) {
        std::string text = ctx->STRING()->getText();
        return text.substr(1, text.size() - 2);  // "var" -> var
    }
    throw DSLValidationException("Unresolvable call argument");
}

// --- Boolean/arithmetic expression tree builders (for when/when_rearming guards) ---

nlohmann::json DSLProgramVisitor::buildVariableNode(PowerEventDSLParser::VariableContext* ctx) {
    std::string attribute = std::any_cast<std::string>(visit(ctx->outputType()->stringAtom()));
    bool is_dynamic_model = ctx->dynamicModelAtom() != nullptr;
    std::string element_id = is_dynamic_model
        ? std::any_cast<std::string>(visit(ctx->dynamicModelAtom()->stringAtom()))
        : std::any_cast<std::string>(visit(ctx->gridElementId()->stringAtom()));
    std::string type_text = is_dynamic_model
        ? fmt::format("\"{}\"", std::any_cast<std::string>(visit(ctx->dynamicModelLibAtom()->stringAtom())))
        : ctx->gridElementType()->getText();
    std::string id;
    try {
        id = is_dynamic_model ? engine_.getDynamicModelOutputId(element_id, attribute)
                              : engine_.getOutputId(element_id, attribute);
    } catch (const std::exception& e) {
        throw DSLValidationException(e.what());
    }
    // "id" is what DSLValueCache is keyed on; "dsl" keeps the source form for describe()
    return nlohmann::json{
        {"type", "var"},
        {"id", id},
        {"dsl", fmt::format("{} \"{}\" output \"{}\"", type_text, element_id, attribute)},
    };
}

nlohmann::json DSLProgramVisitor::buildFactor(PowerEventDSLParser::FactorContext* ctx) {
    nlohmann::json value;
    if (ctx->numericAtom()) {
        value = nlohmann::json{{"type", "const"}, {"value", std::any_cast<double>(visit(ctx->numericAtom()))}};
    } else if (ctx->variable()) {
        value = buildVariableNode(ctx->variable());
    } else {
        value = buildArithExpr(ctx->arithmeticExpr());
    }

    if (ctx->children[0]->getText() == "-") {
        // Negative constant value (e.g. -5)
        if (value.at("type") == "const") {
            value["value"] = -value.at("value").get<double>();  // Folded in, so describe() renders it back as "-5"
            return value;
        }
        // Negative variable (e.g. -P, parsed at (0 - P))
        return nlohmann::json{{"type", "arith"}, {"op", "-"},
                              {"left", {{"type", "const"}, {"value", 0.0}}}, {"right", value}};
    } else {
        return value;
    }
}

nlohmann::json DSLProgramVisitor::buildTerm(PowerEventDSLParser::TermContext* ctx) {
    auto factors = ctx->factor();
    nlohmann::json result = buildFactor(factors[0]);
    size_t factor_idx = 1;
    for (size_t i = 1; i < ctx->children.size(); i++) {
        std::string text = ctx->children[i]->getText();
        if (text == "*" || text == "/") {
            nlohmann::json right = buildFactor(factors[factor_idx++]);
            result = nlohmann::json{{"type", "arith"}, {"op", text}, {"left", result}, {"right", right}};
        }
    }
    return result;
}

nlohmann::json DSLProgramVisitor::buildArithExpr(PowerEventDSLParser::ArithmeticExprContext* ctx) {
    auto terms = ctx->term();
    nlohmann::json result = buildTerm(terms[0]);
    size_t term_idx = 1;
    for (size_t i = 1; i < ctx->children.size(); i++) {
        std::string text = ctx->children[i]->getText();
        if (text == "+" || text == "-") {
            nlohmann::json right = buildTerm(terms[term_idx++]);
            result = nlohmann::json{{"type", "arith"}, {"op", text}, {"left", result}, {"right", right}};
        }
    }
    return result;
}

nlohmann::json DSLProgramVisitor::buildComparisonExpr(PowerEventDSLParser::ComparisonExprContext* ctx) {
    auto left = buildArithExpr(ctx->arithmeticExpr(0));
    auto right = buildArithExpr(ctx->arithmeticExpr(1));
    std::string op = ctx->comparison()->getText();
    return nlohmann::json{{"type", "cmp"}, {"op", op}, {"left", left}, {"right", right}};
}

nlohmann::json DSLProgramVisitor::buildBoolAtomic(PowerEventDSLParser::BooleanAtomicContext* ctx) {
    if (ctx->comparisonExpr()) return buildComparisonExpr(ctx->comparisonExpr());
    return nlohmann::json{{"type", "bool"}, {"value", ctx->booleanLiteral()->getText() == "true"}};
}

nlohmann::json DSLProgramVisitor::buildBoolFactor(PowerEventDSLParser::BooleanFactorContext* ctx) {
    if (ctx->booleanAtomic()) return buildBoolAtomic(ctx->booleanAtomic());
    return buildBoolExpr(ctx->booleanExpr());
}

nlohmann::json DSLProgramVisitor::buildBoolTerm(PowerEventDSLParser::BooleanTermContext* ctx) {
    auto factors = ctx->booleanFactor();
    if (factors.size() == 1) return buildBoolFactor(factors[0]);
    nlohmann::json operands = nlohmann::json::array();
    for (auto* f : factors) operands.push_back(buildBoolFactor(f));
    return nlohmann::json{{"type", "and"}, {"operands", operands}};
}

nlohmann::json DSLProgramVisitor::buildBoolExpr(PowerEventDSLParser::BooleanExprContext* ctx) {
    auto terms = ctx->booleanTerm();
    if (terms.size() == 1) return buildBoolTerm(terms[0]);
    nlohmann::json operands = nlohmann::json::array();
    for (auto* t : terms) operands.push_back(buildBoolTerm(t));
    return nlohmann::json{{"type", "or"}, {"operands", operands}};
}
