/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLEngine.h"
#include "DslKeywords.h"
#include "../utils/TomlExtension.h"
#include "Expr/DSLExprEval.h"
#include "DSLParserDriver.h"
#include "DSLProgramVisitor.h"
#include "Information.h"
#include "Orchestrator.h"

#include <antlr4-c3/CodeCompletionCore.hpp>
#include <spdlog/spdlog.h>

#include <algorithm>
#include <fstream>
#include <sstream>

// Clickhouse table where the Engine dump is stored
static constexpr const char* DUMP_TABLE = "DSLEngineDump";

/**
 * The replay log is a diagnostic/debug artifact, so it is stored in a temp dir.
 * It is also uploaded via ClickHouseLogger::logOutputFile on shutdown.
 */
static std::filesystem::path replayLogPath() {
    std::filesystem::path dir = std::filesystem::path("/tmp") / Orchestrator::get().getSimulationName();
    std::filesystem::create_directories(dir);
    return dir / "dsl_replay.dsl";
}

/**
 * Recursively gathers the execution/interval times of every action/ramp descendant of a function call
 * (flattening nested calls), so the call itself can be placed on a timeline. ConditionalEvent descendants
 * contribute nothing, since they have no fixed schedule of their own.
 */
static void collectDescendantTimes(const std::unordered_map<unsigned long, std::shared_ptr<DSLEvent>>& events,
                                    unsigned long id, std::vector<double>& times) {
    if (!events.contains(id)) return;
    auto* event = events.at(id).get();
    if (auto* action = dynamic_cast<ActionEvent*>(event)) {
        times.push_back(action->getExecutionTime());
    } else if (auto* ramp = dynamic_cast<RampEvent*>(event)) {
        times.push_back(ramp->getParameters().interval_start);
        times.push_back(ramp->getParameters().interval_end);
    } else if (auto* call = dynamic_cast<FunctionCallEvent*>(event)) {
        for (auto child_id : call->childEventIds()) {
            collectDescendantTimes(events, child_id, times);
        }
    }
}

static const char* statusToString(DSLStatus status) {
    switch (status) {
        case DSLStatus::Ready: return "ready";
        case DSLStatus::Ongoing: return "ongoing";
        case DSLStatus::Completed: return "completed";
        case DSLStatus::Interrupted: return "interrupted";
    }
    throw std::runtime_error("Unknown DSLStatus: " + std::to_string(static_cast<int>(status)));
}

DSLEngine::DSLEngine(bool with_subscriptions, ScenarioHandlerInterface& scenario_handler, DynawoInterfaceInterface& dynawo_interface, ClickHouseLoggerInterface& logger, double start_time) : scenario_handler_(scenario_handler),
dynawo_interface_(dynawo_interface),
logger_(logger),
replay_logger_(replayLogPath()),
start_time_(start_time),
tick_index_(1) {
    top_level_scope_ = Scope::newFrame(nullptr, "run");

    auto& config = Orchestrator::get().getConfig();
    period_ = get_or_throw<double>(config, {"master", "period"});
    next_tick_time_ = start_time_ + tick_index_ * period_;

    if (with_subscriptions) {
        initSubscriptions();
        Orchestrator::get().scheduleEvent(next_tick_time_, makeCallback<&DSLEngine::goToNextTimeStep>(this));
    }

    auto dsl_file = get_or_continue<std::string>(config, {"input_files", "dsl_file"});
    if (dsl_file) {
        auto path = Orchestrator::get().getWorkingDir() / dsl_file.value();
        std::ifstream stream(path);
        if (!stream.is_open()) {
            throw std::invalid_argument("DSLEngine: could not open dsl_file " + path.string());
        }
        std::string source((std::istreambuf_iterator<char>(stream)), std::istreambuf_iterator<char>());
        initial_script_ = source;
        loadScript(source, path.filename().string());
        value_cache_.applyPendingWatches();
    }
}

DSLEngine::DSLEngine(ScenarioHandlerInterface& scenario_handler, DynawoInterfaceInterface& dynawo_interface, ClickHouseLoggerInterface& logger, double time) :
scenario_handler_(scenario_handler),
dynawo_interface_(dynawo_interface),
logger_(logger),
replay_logger_(replayLogPath()),
start_time_(time),
tick_index_(1) {
    auto string_buf = logger_.loadDump(DUMP_TABLE, time);
    std::istringstream ss(string_buf);
    ser20::BinaryInputArchive ar(ss);
    ar(*this);

    next_tick_time_ = start_time_ + tick_index_ * period_;

    initSubscriptions();
    postLoadFixup();
    value_cache_.applyPendingWatches();
    Orchestrator::get().scheduleEvent(next_tick_time_, makeCallback<&DSLEngine::goToNextTimeStep>(this));
}

DSLEngine::~DSLEngine() {
    double now = Orchestrator::get().getCurrentTime();
    // Log the current status of ramps at the time of shutdown
    for (auto& id : watch_list_.rampIds()) {
        if (!events_.contains(id)) continue;
        auto* ramp = dynamic_cast<RampEvent*>(events_.at(id).get());
        // Add description for ongoing but not yet completed ramps
        if (ramp && ramp->getStatus() == DSLStatus::Ongoing) {
            replay_logger_.logLine(ramp->describeInterval(now));
        }
    }
    replay_logger_.close();
    // Upload the diagnostic/debug dsl_replay file to Clickhouse
    logger_.logOutputFile(replay_logger_.path());
}

void DSLEngine::initSubscriptions() {
    Orchestrator::get().subscribeTo<ActualMeasurement, &DSLEngine::onActualMeasurement>(this);
    Orchestrator::get().subscribeTo<ActualControl, &DSLEngine::onActualControl>(this);
    Orchestrator::get().subscribeTo<DumpStateEvent, &DSLEngine::handleDumpStateEvent>(this);
}

void DSLEngine::postLoadFixup() {
    // Runtime-only watch/subscription handles are not serialized (only DSLEvent's own data is), so we need to repopulate them
    for (auto& [id, event] : events_) {
        if (auto* action = dynamic_cast<ActionEvent*>(event.get())) {
            if (action->getStatus() == DSLStatus::Ready) {
                point_queue_.insert(action->getExecutionTime(), id);
            }
        } else if (auto* ramp = dynamic_cast<RampEvent*>(event.get())) {
            if (ramp->getStatus() == DSLStatus::Ready || ramp->getStatus() == DSLStatus::Ongoing) {
                watch_list_.addRamp(id);
                value_cache_.watchIds(ramp->startOutputIds());
            }
        } else if (auto* cond = dynamic_cast<ConditionalEvent*>(event.get())) {
            if (cond->getStatus() == DSLStatus::Ready || cond->getStatus() == DSLStatus::Ongoing) {
                watch_list_.addConditional(id);
                value_cache_.watchIds(collectReferencedIds(cond->getConditionExpr()));
            }
        }
    }
}

unsigned long DSLEngine::newEventId() {
    return next_event_id_++;
}

std::shared_ptr<FunctionDefinition> DSLEngine::lookupFunction(const std::string& name) const {
    return functions_.contains(name) ? functions_.at(name) : nullptr;
}

void DSLEngine::registerFunction(std::shared_ptr<FunctionDefinition> def) {
    functions_[def->name] = std::move(def);
}

std::string DSLEngine::getOutputId(const std::string& iidm_id, const std::string& attribute) const {
    return dynawo_interface_.getOutputFromIidm(iidm_id, attribute);
}

std::optional<double> DSLEngine::currentValue(const std::string& output_id) const {
    return value_cache_.get(output_id);
}

std::string DSLEngine::getDynamicModelOutputId(const std::string& dynamic_model, const std::string& attribute) const {
    return dynawo_interface_.getOutputFromDynamicModel(dynamic_model, attribute);
}

std::vector<std::string> DSLEngine::listIidmIds(const std::string& pypowsybl_type) const {
    return dynawo_interface_.listIidmIds(pypowsybl_type);
}

std::vector<std::string> DSLEngine::listDynamicModelIds(const std::string& model_lib) const {
    return dynawo_interface_.listDynamicModelIds(model_lib, DynamicModelDirection::Input);
}

void DSLEngine::registerPendingRamp(const std::string& iidm_id, const std::string& attribute, double start, double end) {
    pending_ramps_.push_back({iidm_id, attribute, start, end});
}

bool DSLEngine::hasActiveRampOn(const std::string& iidm_id, const std::string& attribute, double start, double end,
                                 std::optional<unsigned long> exclude_id) const {
    for (auto& pending : pending_ramps_) {
        if (pending.iidm_id != iidm_id || pending.attribute != attribute) continue;
        if (start <= pending.interval_end && end >= pending.interval_start) {
            return true;
        }
    }
    for (auto& id : watch_list_.rampIds()) {
        if (exclude_id && id == *exclude_id) continue;
        if (!events_.contains(id)) continue;
        auto* ramp = dynamic_cast<RampEvent*>(events_.at(id).get());
        if (!ramp) continue;
        if (ramp->getStatus() != DSLStatus::Ready && ramp->getStatus() != DSLStatus::Ongoing) continue;
        if (!ramp->isTargeting(iidm_id, attribute)) continue;
        auto& parameters = ramp->getParameters();
        if (start <= parameters.interval_end && end >= parameters.interval_start) {
            return true;
        }
    }
    return false;
}

std::vector<std::unique_ptr<DSLEvent>> DSLEngine::expandFunctionCall(
    const std::string& function_name, const std::vector<ParamValue>& args, double call_time,
    std::shared_ptr<const Scope> caller_scope, unsigned long call_event_id,
    const std::string& source_name) {

    auto func_def = lookupFunction(function_name);
    if (!func_def) throw DSLValidationException("Unknown function: " + function_name);
    if (std::find(expansion_stack_.begin(), expansion_stack_.end(), function_name) != expansion_stack_.end()) {
        std::string chain;
        for (auto& name : expansion_stack_) chain += name + " -> ";
        throw DSLValidationException("Recursive function call: " + chain + function_name);
    }
    expansion_stack_.push_back(function_name);
    struct PopOnExit {
        std::vector<std::string>& stack;
        ~PopOnExit() { stack.pop_back(); }
    } pop_on_exit{expansion_stack_};

    if (args.size() != func_def->param_names.size()) {
        throw DSLValidationException(function_name + ": expected " + std::to_string(func_def->param_names.size())
            + " argument(s), got " + std::to_string(args.size()));
    }

    auto invocation_scope = Scope::newFrame(caller_scope, std::to_string(call_event_id));
    for (size_t i = 0; i < func_def->param_names.size(); i++) {
        invocation_scope->bindParam(func_def->param_names[i], args[i]);
    }

    auto parse_result = parseFunctionBody(func_def->body_text);
    auto* wrapper_func = parse_result->program()->statement(0)->functionDef();

    DSLProgramVisitor visitor(*this, scenario_handler_, iidm_mapping_, ifl_mapping_, call_time,
                               invocation_scope, call_event_id, source_name);
    visitor.visitFunctionBody(wrapper_func);

    std::vector<std::unique_ptr<DSLEvent>> result;
    for (auto& ev : visitor.batch()) {
        result.push_back(std::move(ev));
    }
    return result;
}

void DSLEngine::commitBatch(std::vector<std::unique_ptr<DSLEvent>>& batch) {
    for (auto& event : batch) {
        unsigned long id = event->getId();
        auto tag = event->getTag();
        std::shared_ptr<DSLEvent> shared_event = std::move(event);

        if (auto* cond = dynamic_cast<ConditionalEvent*>(shared_event.get())) {
            replay_logger_.logLine(cond->describe());
            watch_list_.addConditional(id);
            value_cache_.watchIds(collectReferencedIds(cond->getConditionExpr()));
        } else if (auto* action = dynamic_cast<ActionEvent*>(shared_event.get())) {
            point_queue_.insert(action->getExecutionTime(), id);
        } else if (auto* ramp = dynamic_cast<RampEvent*>(shared_event.get())) {
            watch_list_.addRamp(id);
            value_cache_.watchIds(ramp->startOutputIds());
        }
        // FunctionCallEvent: nothing to schedule since expandFunctionCall flattens nested calls into one batch

        if (tag) tag_owners_[*tag].push_back(id);
        events_[id] = std::move(shared_event);
    }
    batch.clear();
}

std::vector<unsigned long> DSLEngine::collectCallSubtree(unsigned long id) const {
    std::vector<unsigned long> subtree;
    if (!events_.contains(id)) return subtree;
    if (auto* call = dynamic_cast<FunctionCallEvent*>(events_.at(id).get())) {
        for (auto& child_id : call->childEventIds()) {
            auto nested = collectCallSubtree(child_id);
            subtree.insert(subtree.end(), nested.begin(), nested.end());
        }
    }
    subtree.push_back(id);
    return subtree;
}

void DSLEngine::releaseEvent(unsigned long id) {
    if (!events_.contains(id)) return;
    point_queue_.cancel(id);
    watch_list_.cancel(id);
    if (auto* cond = dynamic_cast<ConditionalEvent*>(events_.at(id).get())) {
        value_cache_.unwatchIds(collectReferencedIds(cond->getConditionExpr()));
    } else if (auto* ramp = dynamic_cast<RampEvent*>(events_.at(id).get())) {
        value_cache_.unwatchIds(ramp->startOutputIds());
    }
}

void DSLEngine::removeReadyEvent(unsigned long id) {
    releaseEvent(id);
    events_.erase(id);
}

bool DSLEngine::isTagCompleted(const std::string& qualified_tag) const {
    if (!tag_owners_.contains(qualified_tag) || tag_owners_.at(qualified_tag).empty()) {
        return false;
    }
    for (auto& id : tag_owners_.at(qualified_tag)) {
        if (!events_.contains(id) || events_.at(id)->getStatus() != DSLStatus::Completed) {
            return false;
        }
    }
    return true;
}

void DSLEngine::propagateStatusToParents(unsigned long child_id) {
    if (!events_.contains(child_id)) {
        return;
    }
    refreshCallsFrom(events_.at(child_id)->getParentEventId());
}

void DSLEngine::refreshCallsFrom(std::optional<unsigned long> parent_id) {
    while (parent_id) {
        if (!events_.contains(*parent_id)) {
            break;
        }
        auto* call_event = dynamic_cast<FunctionCallEvent*>(events_.at(*parent_id).get());
        if (!call_event) {
            break;
        }
        call_event->refreshStatus(events_);
        parent_id = call_event->getParentEventId();
    }
}

/** Whether the caret sits inside a string the user has not closed yet. */
bool insideString(const std::string& partial) {
    return std::count(partial.begin(), partial.end(), '"') % 2 == 1;
}

/**
 * Where the caret is. ANTLR's lexer cannot be handed a half-written string, so an unterminated one is closed
 * before lexing; 'prefix' is the remaining of the string, and filters the suggestions.
 */
struct Caret {
    explicit Caret(const std::string& partial);

    std::string text;  // The partial, with any unterminated string closed
    bool in_string;
    std::string prefix;
    size_t start = 0;  // Where the token being typed begins in the partial

    antlr4::ANTLRInputStream input;
    PowerEventDSLLexer lexer;
    antlr4::CommonTokenStream token_stream;
    PowerEventDSLParser parser;

    std::vector<antlr4::Token*> tokens;
    size_t index = 0;  // The token the caret sits on, or EOF when the text ends on a separator
};

Caret::Caret(const std::string& partial) :
text(insideString(partial) ? partial + '"' : partial),
in_string(insideString(partial)),
input(text),
lexer(&input),
token_stream(&lexer),
parser(&token_stream) {
    if (in_string) {
        start = partial.rfind('"');
        prefix = partial.substr(start + 1);
    } else {
        start = partial.size();
        while (start > 0 && (std::isalnum(static_cast<unsigned char>(partial[start - 1])) || partial[start - 1] == '_')) {
            start--;
        }
        if (start > 0 && partial[start - 1] == '$') start--;
        prefix = partial.substr(start);
    }

    lexer.removeErrorListeners();  // A statement being typed is incomplete by definition, so errors are expected
    parser.removeErrorListeners();
    token_stream.fill();
    tokens = token_stream.getTokens();

    index = (in_string || !prefix.empty()) ? tokens.size() - 2 : tokens.size() - 1;
}

/** The grammar's literal tokens ('func', '{', 'load'...), which ANTLR names T__0, T__1... */
struct Literals {
    std::unordered_map<size_t, std::string> text;  // Token type -> literal, quotes stripped
    size_t lbrace = 0;
    size_t rbrace = 0;
    size_t lparen = 0;
    size_t rparen = 0;

    std::string of(size_t token_type) const {
        auto it = text.find(token_type);
        return it == text.end() ? std::string() : it->second;
    }
};

Literals readLiterals(const antlr4::dfa::Vocabulary& vocabulary) {
    Literals literals;
    for (size_t type = 1; type <= vocabulary.getMaxTokenType(); type++) {
        std::string name{vocabulary.getLiteralName(type)};
        if (name.size() < 2) continue;  // No literal: IDENTIFIER, STRING, NUMBER...
        std::string literal = name.substr(1, name.size() - 2);
        literals.text[type] = literal;
        if (literal == "{") literals.lbrace = type;
        else if (literal == "}") literals.rbrace = type;
        else if (literal == "(") literals.lparen = type;
        else if (literal == ")") literals.rparen = type;
    }
    return literals;
}

bool isElementType(const std::string& word) {
    return std::find(DSL_ELEMENT_TYPES.begin(), DSL_ELEMENT_TYPES.end(), word) != DSL_ELEMENT_TYPES.end();
}

/**
 * Parameters of the function whose body holds the caret. Used to autocomplete $var, e.g. in
 * func f(alpha, beta) { at 0 seconds, open switch $...
 */
std::vector<std::string> enclosingParameters(const std::vector<antlr4::Token*>& tokens, size_t caret, const Literals& literals) {
    size_t depth = 0;
    size_t brace = 0;
    for (size_t i = caret; i-- > 0;) {
        size_t type = tokens[i]->getType();
        if (type == literals.rbrace) {
            depth++;
        } else if (type == literals.lbrace) {
            if (depth == 0) { brace = i; break; }
            depth--;
        }
    }
    if (brace == 0 || tokens[brace - 1]->getType() != literals.rparen) return {};

    std::vector<std::string> parameters;
    for (size_t i = brace - 1; i-- > 0;) {
        size_t type = tokens[i]->getType();
        if (type == literals.lparen) return parameters;  // Stops before the function's own name
        if (type == PowerEventDSLParser::IDENTIFIER) parameters.push_back(tokens[i]->getText());
    }
    return {};
}

DSLCompletions DSLEngine::complete(const std::string& partial) const {
    std::lock_guard<std::mutex> lock(mutex_);

    Caret caret(partial);
    static const Literals literals = readLiterals(caret.parser.getVocabulary());

    // The rules that cannot be autogenerated from the grammar alone, e.g. mapping elements, etc.
    c3::CodeCompletionCore core(&caret.parser);
    core.preferredRules = {
        PowerEventDSLParser::RuleSwitchId,
        PowerEventDSLParser::RuleLineId,
        PowerEventDSLParser::RuleTransformerId,
        PowerEventDSLParser::RuleGridElementId,
        PowerEventDSLParser::RuleInputType,
        PowerEventDSLParser::RuleOutputType,
        PowerEventDSLParser::RuleClusterId,
        PowerEventDSLParser::RuleCallExpr,
        PowerEventDSLParser::RuleVarRef,
        PowerEventDSLParser::RuleDynamicModelLibAtom,
        PowerEventDSLParser::RuleDynamicModelAtom,
        PowerEventDSLParser::RuleNodeId,
    };
    auto candidates = core.collectCandidates(caret.index);

    std::vector<std::pair<std::string, bool>> suggestions;
    auto append = [&](const std::vector<std::string>& values, bool quoted) {
        for (auto& value : values) {
            suggestions.emplace_back(value, quoted);
        }
    };

    /** Element type governing the caret's slot, e.g. "load" in: decrease load "01_1" input " */
    auto governing_element_type = [&]() -> std::string {
        for (size_t i = caret.index; i-- > 0;) {
            std::string literal = literals.of(caret.tokens[i]->getType());
            if (isElementType(literal)) {
                return literal;
            }
        }
        return {};
    };

    /** Element id governing the caret's slot: the one whose attributes are being named, or the model library
        whose models are */
    auto governing_element_id = [&]() -> std::string {
        for (size_t i = caret.index; i-- > 0;) {
            if (caret.tokens[i]->getType() == PowerEventDSLParser::STRING) {
                std::string text = caret.tokens[i]->getText();
                return text.substr(1, text.size() - 2);
            }
        }
        return {};
    };

    /**
     * Model library governing the caret's slot. Not simply the string before it: inside a list the string before
     * the caret is a sibling model, so the nearest string that actually names a library is what governs.
     */
    auto governing_model_lib = [&](DynamicModelDirection direction) -> std::string {
        auto libs = dynawo_interface_.listDynamicModelLibs(direction);
        for (size_t i = caret.index; i-- > 0;) {
            if (caret.tokens[i]->getType() != PowerEventDSLParser::STRING) continue;
            std::string text = caret.tokens[i]->getText();
            text = text.substr(1, text.size() - 2);
            if (std::find(libs.begin(), libs.end(), text) != libs.end()) return text;
        }
        return {};
    };

    /** Nearest of 'node', 'from' and 'to' before the caret, which is the keyword that opened this slot. */
    auto slotKeyword = [&]() -> std::string {
        for (size_t i = caret.index; i-- > 0;) {
            std::string literal = literals.of(caret.tokens[i]->getType());
            if (literal == "node" || literal == "from" || literal == "to") return literal;
        }
        return {};
    };

    /** The 'from' node of the link being written, so a 'to' slot only offers links that exist. */
    auto linkSource = [&]() -> std::string {
        for (size_t i = caret.index; i-- > 1;) {
            if (literals.of(caret.tokens[i - 1]->getType()) != "from") continue;
            if (caret.tokens[i]->getType() != PowerEventDSLParser::STRING) return {};
            std::string text = caret.tokens[i]->getText();
            return text.substr(1, text.size() - 2);
        }
        return {};
    };

    auto appendIidmIds = [&](const std::string& element_type) {
        if (element_type.empty()) return;
        try {
            append(dynawo_interface_.listIidmIds(element_type), true);
        } catch (const std::exception&) {
            // No element for this type, return nothing instead of throw
        }
    };

    // Grammar literals can never appear between quotes, whatever the ATN says is valid at that token
    if (!caret.in_string) {
        for (auto& [token_type, _following] : candidates.tokens) {
            std::string literal = literals.of(token_type);
            if (!literal.empty()) {
                suggestions.emplace_back(literal, false);
            }
        }
    }

    bool takes_variable = false;
    for (auto& [rule, candidate] : candidates.rules) {
        // The same two rules name a dynamic model in an action's target and in a condition's variable. The rule
        // path c3 reports says which of the two the caret is in, and so which half of the mapping to offer.
        auto direction = std::find(candidate.ruleList.begin(), candidate.ruleList.end(),
                                    PowerEventDSLParser::RuleVariable) != candidate.ruleList.end()
            ? DynamicModelDirection::Output : DynamicModelDirection::Input;
        takes_variable = takes_variable || rule != PowerEventDSLParser::RuleCallExpr;
        switch (rule) {
            case PowerEventDSLParser::RuleSwitchId: appendIidmIds("switch"); break;
            case PowerEventDSLParser::RuleLineId: appendIidmIds("line"); break;
            // One DSL keyword covers both winding counts, so both populations are offered
            case PowerEventDSLParser::RuleTransformerId:
                appendIidmIds("2_windings_transformer");
                appendIidmIds("3_windings_transformer");
                break;
            case PowerEventDSLParser::RuleGridElementId: appendIidmIds(governing_element_type()); break;
            // An id is either an IIDM equipment or a dynamic model, never both, so one of the two comes back empty
            case PowerEventDSLParser::RuleInputType:
                append(dynawo_interface_.listInputAttributes(governing_element_id()), true);
                append(dynawo_interface_.listDynamicModelInputKinds(governing_element_id()), true);
                break;
            case PowerEventDSLParser::RuleDynamicModelLibAtom: append(dynawo_interface_.listDynamicModelLibs(direction), true); break;
            case PowerEventDSLParser::RuleDynamicModelAtom: append(dynawo_interface_.listDynamicModelIds(governing_model_lib(direction), direction), true); break;
            case PowerEventDSLParser::RuleOutputType:
                append(dynawo_interface_.listOutputAttributes(governing_element_id()), true);
                append(dynawo_interface_.listDynamicModelOutputKinds(governing_element_id()), true);
                break;
            case PowerEventDSLParser::RuleClusterId: append(top_level_scope_->clusterNames(), true); break;
            // One rule serves 'node X', 'link from X' and 'link to X'. 'node X' and 'link from X' can be any node.
            // 'link to X' can only be a valid destination from the current node.
            case PowerEventDSLParser::RuleNodeId:
                if (slotKeyword() == "to") {
                    append(scenario_handler_.listDestinations(linkSource()), true);
                } else {
                    append(scenario_handler_.listNodes(), true);
                }
                break;
            case PowerEventDSLParser::RuleCallExpr:
                for (auto& [name, _definition] : functions_) {
                    suggestions.emplace_back(name, false);
                }
                break;
            default: break;
        }
    }

    // Every slot that takes a quoted name takes a $parameter instead, so c3 reports the outer rule and never
    // descends to varRef there. Inside the quotes themselves only the name is valid.
    if (takes_variable && !caret.in_string) {
        for (auto& name : enclosingParameters(caret.tokens, caret.index, literals)) {
            suggestions.emplace_back("$" + name, false);
        }
    }

    DSLCompletions completions;
    completions.replace_from = caret.start;
    for (auto& [value, quoted] : suggestions) {
        if (value.compare(0, caret.prefix.size(), caret.prefix) != 0) continue;
        completions.suggestions.push_back(quoted ? '"' + value + '"' : value);
    }
    // Sort and delete duplicates
    std::sort(completions.suggestions.begin(), completions.suggestions.end());
    auto duplicates = std::unique(completions.suggestions.begin(), completions.suggestions.end());
    completions.suggestions.erase(duplicates, completions.suggestions.end());

    if (completions.suggestions.size() > MAX_COMPLETIONS) {
        completions.suggestions.resize(MAX_COMPLETIONS);
    }
    return completions;
}

nlohmann::json DSLEngine::listEvents() const {
    std::lock_guard<std::mutex> lock(mutex_);
    nlohmann::json result = nlohmann::json::array();
    for (auto& [id, event] : events_) {
        nlohmann::json entry;
        entry["id"] = id;
        entry["status"] = statusToString(event->getStatus());
        entry["tag"] = event->getTag() ? nlohmann::json(*event->getTag()) : nlohmann::json();
        entry["source"] = event->getSource();
        entry["describe"] = event->describe();

        if (auto* action = dynamic_cast<ActionEvent*>(event.get())) {
            entry["kind"] = "action";
            entry["execution_time"] = action->getExecutionTime();
        } else if (auto* ramp = dynamic_cast<RampEvent*>(event.get())) {
            entry["kind"] = "ramp";
            entry["interval_start"] = ramp->getParameters().interval_start;
            entry["interval_end"] = ramp->getParameters().interval_end;
        } else if (dynamic_cast<ConditionalEvent*>(event.get())) {
            entry["kind"] = "conditional";
        } else if (dynamic_cast<FunctionCallEvent*>(event.get())) {
            entry["kind"] = "function_call";
            std::vector<double> times;
            collectDescendantTimes(events_, id, times);
            if (times.empty()) {
                // No descendant has a fixed schedule of its own (e.g. only conditionals): fall back to the moment the call itself was made.
                entry["execution_time"] = event->getGenerationTime();
            } else {
                double min_time = std::ranges::min(times);
                double max_time = std::ranges::max(times);
                if (min_time == max_time) {
                    entry["execution_time"] = min_time;
                } else {
                    entry["interval_start"] = min_time;
                    entry["interval_end"] = max_time;
                }
            }
        }

        result.push_back(std::move(entry));
    }
    return result;
}

bool DSLEngine::cancelEvent(unsigned long id) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!events_.contains(id)) return false;

    auto status = events_.at(id)->getStatus();
    if (status == DSLStatus::Completed || status == DSLStatus::Interrupted) return false;

    if (status == DSLStatus::Ready) {
        auto parent_id = events_.at(id)->getParentEventId();
        // Delete self and all children
        for (auto& subtree_id : collectCallSubtree(id)) {
            removeReadyEvent(subtree_id);
        }
        refreshCallsFrom(parent_id);  // Notify parent of deletion
    } else {  // Ongoing
        if (auto* call = dynamic_cast<FunctionCallEvent*>(events_.at(id).get())) {
            for (auto& interrupted_id : call->interruptCascading(events_)) {
                // Release children
                releaseEvent(interrupted_id);
            }
        } else {
            events_.at(id)->interrupt();
            releaseEvent(id);
        }
        propagateStatusToParents(id);
    }
    return true;
}

unsigned long DSLEngine::replaceEventIfReady(unsigned long id, const std::string& new_dsl_text, const std::string& source_name) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!events_.contains(id) || events_.at(id)->getStatus() != DSLStatus::Ready) {
        throw DSLValidationException("Event " + std::to_string(id) + " is not Ready (or doesn't exist)");
    }

    pending_ramps_.clear();
    DSLParseResult parsed(new_dsl_text);
    auto statements = parsed.program()->statement();
    if (statements.size() != 1 || !statements[0]->eventDef()) {
        throw DSLValidationException("Replacement text must be exactly one event statement");
    }

    // Use time_context_ = 0 instead of the current (i.e. use absolute times) as the original dsl command comes from describe(), which
    // renders already-resolved absolute times
    // exclude_event_id = id: 'id', so that ramp overlap check does not collide with itself (the event being replaced is only deleted
    // once the new is proven valid).
    auto parent_id = events_.at(id)->getParentEventId();
    DSLProgramVisitor visitor(*this, scenario_handler_, iidm_mapping_, ifl_mapping_,
                              0.0, top_level_scope_, parent_id, source_name, id);
    visitor.visit(statements[0]->eventDef());
    if (visitor.batch().size() != 1) {
        throw DSLValidationException("Replacement text must resolve to exactly one event");
    }

    double now = Orchestrator::get().getCurrentTime();
    auto& new_event = visitor.batch().front();
    if (auto* action = dynamic_cast<ActionEvent*>(new_event.get())) {
        if (action->getExecutionTime() < now) {
            throw DSLValidationException("Replacement time (t=" + std::to_string(action->getExecutionTime())
                + ") is in the past (now=" + std::to_string(now) + ")");
        }
    } else if (auto* ramp = dynamic_cast<RampEvent*>(new_event.get())) {
        if (ramp->getParameters().interval_start < now) {
            throw DSLValidationException("Replacement start time (t=" + std::to_string(ramp->getParameters().interval_start)
                + ") is in the past (now=" + std::to_string(now) + ")");
        }
    }

    removeReadyEvent(id);
    unsigned long new_id = visitor.batch().front()->getId();
    commitBatch(visitor.batch());

    // Notify parents of edition
    if (parent_id && events_.contains(*parent_id)) {
        if (auto* call = dynamic_cast<FunctionCallEvent*>(events_.at(*parent_id).get())) {
            call->replaceChildId(id, new_id);
        }
    }
    // The replacement inherits the tags the old event owned
    for (auto& [tag, owners] : tag_owners_) {
        std::replace(owners.begin(), owners.end(), id, new_id);
    }
    refreshCallsFrom(parent_id);
    return new_id;
}

void DSLEngine::loadScript(const std::string& source_text, const std::string& source_name) {
    std::lock_guard<std::mutex> lock(mutex_);
    try {
        DSLParseResult parsed(source_text);
        for (auto* statement : parsed.program()->statement()) {
            pending_ramps_.clear();
            DSLProgramVisitor visitor(*this, scenario_handler_, iidm_mapping_, ifl_mapping_,
                                       Orchestrator::get().getCurrentTime(), top_level_scope_, std::nullopt, source_name);
            if (statement->functionDef()) {
                visitor.registerFunctionDef(statement->functionDef());
            } else if (statement->clusterDef()) {
                visitor.visit(statement->clusterDef());
            } else if (statement->eventDef()) {
                visitor.visit(statement->eventDef());
                commitBatch(visitor.batch());
            }
        }
    } catch (const std::invalid_argument&) {  // Includes DSLValidationException
        throw;  // Propagate as-is
    } catch (const std::exception& e) {
        throw std::invalid_argument(e.what());
    }
}

void DSLEngine::applyDuePointActions(double now) {
    for (auto& id : point_queue_.popDue(now)) {
        if (!events_.contains(id)) continue;
        auto* action = dynamic_cast<ActionEvent*>(events_.at(id).get());
        if (!action) continue;
        action->execute(scenario_handler_);
        replay_logger_.logLine(action->describe());
        propagateStatusToParents(id);
    }
}

void DSLEngine::expandTriggeredCall(unsigned long conditional_id, const std::string& call_source, double now) {
    std::string source_name = events_.contains(conditional_id) ? events_.at(conditional_id)->getSource() : "dsl";
    try {
        pending_ramps_.clear();
        DSLParseResult parsed(call_source + ";");
        DSLProgramVisitor visitor(*this, scenario_handler_, iidm_mapping_, ifl_mapping_,
                                   now, top_level_scope_, conditional_id, source_name);
        visitor.visit(parsed.program()->statement(0)->eventDef());
        commitBatch(visitor.batch());
    } catch (const std::exception& e) {
        // The call was validated when the trigger was written, so this should only occur if the mapping change which it does not.
        spdlog::error("Trigger {} fired but its call could not be expanded: {}", conditional_id, e.what());
    }
}

void DSLEngine::goToNextTimeStep() {
    std::lock_guard<std::mutex> lock(mutex_);
    // Apply watch changes requested since the last tick (new conditional events from a DSLWebInterface thread)
    // Done here on the simulation thread, so that the DSLValueCache's ~500k/s measurement path stays lock-free.
    value_cache_.applyPendingWatches();

    double now = next_tick_time_;

    applyDuePointActions(now);

    std::vector<unsigned long> completed_ramps;
    for (auto& id : watch_list_.rampIds()) {
        if (!events_.contains(id)) continue;
        auto* ramp = dynamic_cast<RampEvent*>(events_.at(id).get());
        if (!ramp) continue;
        bool was_done = ramp->getStatus() == DSLStatus::Completed || ramp->getStatus() == DSLStatus::Interrupted;
        ramp->applyTick(scenario_handler_, *this, now);
        bool is_done = ramp->getStatus() == DSLStatus::Completed || ramp->getStatus() == DSLStatus::Interrupted;
        if (!was_done && is_done) {
            replay_logger_.logLine(ramp->describeInterval(now));
            propagateStatusToParents(id);
            completed_ramps.push_back(id);
        }
    }
    watch_list_.removeRamps(completed_ramps);

    std::vector<unsigned long> done_conditionals;
    std::vector<std::pair<unsigned long, std::string>> fired_calls;
    for (auto& id : watch_list_.conditionalIds()) {
        if (!events_.contains(id)) continue;
        auto* cond = dynamic_cast<ConditionalEvent*>(events_.at(id).get());
        if (!cond) continue;

        bool was_done = cond->getStatus() == DSLStatus::Completed || cond->getStatus() == DSLStatus::Interrupted;
        if (!was_done) {
            bool condition_is_true = false;
            switch (cond->getKind()) {
                case TriggerKind::After:
                    condition_is_true = cond->getDependencyTag() && isTagCompleted(*cond->getDependencyTag());
                    break;
                case TriggerKind::When:
                case TriggerKind::WhenRearming:
                    condition_is_true = BooleanExpression{cond->getConditionExpr()}.evaluate(value_cache_);
                    break;
            }
            if (cond->evaluate(scenario_handler_, condition_is_true) && !cond->getActionCallSource().empty()) {
                fired_calls.push_back({id, cond->getActionCallSource()});
            }
        }

        bool is_done = cond->getStatus() == DSLStatus::Completed || cond->getStatus() == DSLStatus::Interrupted;
        if (!was_done && is_done) {
            propagateStatusToParents(id);
            done_conditionals.push_back(id);
            value_cache_.unwatchIds(collectReferencedIds(cond->getConditionExpr()));
        }
    }
    watch_list_.removeConditionals(done_conditionals);
    for (auto& [conditional_id, call_source] : fired_calls) {
        expandTriggeredCall(conditional_id, call_source, now);
    }
    if (!fired_calls.empty()) {
        // Apply the events generated for 'now' from the fired calls
        applyDuePointActions(now);
    }

    tick_index_++;
    next_tick_time_ = start_time_ + tick_index_ * period_;
    Orchestrator::get().scheduleEvent(next_tick_time_, makeCallback<&DSLEngine::goToNextTimeStep>(this));
}

void DSLEngine::onActualMeasurement(const ActualMeasurement& info) {
    value_cache_.onActualMeasurement(info);
}

void DSLEngine::onActualControl(const ActualControl& info) {
    value_cache_.onActualControl(info);
}

void DSLEngine::handleDumpStateEvent(const DumpStateEvent& event) {
    std::ostringstream bin(std::ios::binary);
    {
        std::lock_guard<std::mutex> lock(mutex_);  // Lock against DSLWebInterface thread
        ser20::BinaryOutputArchive archive(bin);
        archive(*this);
    }
    logger_.saveDump(DUMP_TABLE, event.time, bin.str());
}
