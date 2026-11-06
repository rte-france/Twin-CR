/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_EVENT_H
#define DSL_EVENT_H

#include "../utils/ScenarioHandlerInterface.h"
#include "Mapping/IIDMMapping.h"
#include "SerialisationHelper.h"

#include <ser20/types/polymorphic.hpp>

#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

enum class DSLStatus { Ready, Ongoing, Completed, Interrupted };

class DSLEngine;

/**
 * Throws std::logic_error if 'payload' carries a scheduling time of its own ("t_start"/"t_start_from_now").
 * The DSL engine is only allowed to generate "now" events as scheduled events could be lost in a dump/reload cycle (events in the Orchestrator queue are not serialised)
 */
void assertUntimedPayload(const nlohmann::json& payload);

/**
 * Base class for all DSL event.
 * Every subtype should resolve its behavior into plain data at commit time (e.g. a JSON payload, ramp targets, a condition
 * expression tree, or child event ids), never a callback, so (de)serialisation (for dump/load the state of the engine) is straightforward.
 * The 'dsl_text' is the DSL source that created the event with references resolved (e.g. a cluster def is replaced by the list of ids contained in the cluster)
 */
class DSLEvent : public std::enable_shared_from_this<DSLEvent> {
    public:
        DSLEvent() = default; // Required for deserialization
        DSLEvent(unsigned long id, std::string dsl_text, double generation_time, std::string source, std::optional<unsigned long> parent_event_id) :
            id_(id),
            dsl_text_(std::move(dsl_text)),
            generation_time_(generation_time),
            source_(std::move(source)),
            parent_event_id_(parent_event_id) {}
        virtual ~DSLEvent() = default;

        unsigned long getId() const { return id_; }
        const std::string& getDslText() const { return dsl_text_; }
        double getGenerationTime() const { return generation_time_; }
        const std::string& getSource() const { return source_; }
        DSLStatus getStatus() const { return status_; }
        const std::optional<unsigned long>& getParentEventId() const { return parent_event_id_; }
        const std::optional<std::string>& getTag() const { return tag_; }
        void setTag(std::optional<std::string> tag) { tag_ = std::move(tag); }

        /**
         * "Delete" semantics: a Ready event is removed outright by DSLEngine (not via this call);
         * an Ongoing event is marked Interrupted (retained) via this call. No-op if already interrupted/completed.
         */
        virtual void interrupt() = 0;

        /**
         * Renders this event back into valid DSL syntax (absolute time), for the replay log.
         */
        virtual std::string describe() const { return dsl_text_; }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(id_, dsl_text_, generation_time_, source_, parent_event_id_, tag_, status_);
        }

    protected:
        unsigned long id_ = 0;
        std::string dsl_text_;
        double generation_time_ = 0.0;
        std::string source_;
        std::optional<unsigned long> parent_event_id_;
        std::optional<std::string> tag_; // fully-qualified tag key, if `tagged` was used
        DSLStatus status_ = DSLStatus::Ready;
};
SER20_REGISTER_TYPE(DSLEvent);
CHECK_SERIALIZABLE(DSLEvent);

/**
 * A single point-in-time action.
 * Resolved into ready-to-apply JSON payload(s) for ScenarioHandler at creation time.
 */
class ActionEvent : public DSLEvent {
    public:
        ActionEvent() = default;
        ActionEvent(unsigned long id, std::string dsl_text, double generation_time, std::string source, std::optional<unsigned long> parent_event_id,
            double execution_time, std::vector<nlohmann::json> payloads) :
            DSLEvent(id, std::move(dsl_text), generation_time, std::move(source), parent_event_id),
            execution_time_(execution_time),
            payloads_(std::move(payloads)) {
                for (auto& payload : payloads_) assertUntimedPayload(payload);
            }

        ActionEvent(unsigned long id, std::string dsl_text, double generation_time, std::string source, std::optional<unsigned long> parent_event_id,
            double execution_time, nlohmann::json payload) :
            ActionEvent(id, std::move(dsl_text), generation_time, std::move(source), parent_event_id,
                        execution_time, std::vector<nlohmann::json>{std::move(payload)}) {}

        double getExecutionTime() const { return execution_time_; }
        const std::vector<nlohmann::json>& getPayloads() const { return payloads_; }

        /**
         * Applies every payload via ScenarioHandler::applyScenario(Mode::Execute) and marks Completed.
         */
        void execute(ScenarioHandlerInterface& scenario_handler);

        void interrupt() override {
            if (status_ == DSLStatus::Ready) status_ = DSLStatus::Interrupted;
        }

        std::string describe() const override;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DSLEvent>(this), execution_time_, payloads_);
        }

    private:
        double execution_time_ = 0.0;
        std::vector<nlohmann::json> payloads_;
};
SER20_REGISTER_TYPE(ActionEvent);
CHECK_SERIALIZABLE(ActionEvent);

/**
 * A single element/attribute target within a ramp (a ramp over a list/cluster
 * target has one Target entry per resolved grid element). Which fields are
 * meaningful depends on the owning RampEvent's RampParameters::kind (see below).
 */
struct RampTarget {
    TargetRef target;
    std::string attribute;

    // Value-ramp fields (kind == Value)
    double from_value = 0.0;
    double to_value = 0.0;
    // Set when the statement gave no 'from': the output whose measurement the ramp starts from, and whether it
    // has been read yet. Until it has, the ramp applies nothing.
    std::string start_output_id;
    bool start_resolved = true;

    // Multiplier-ramp fields (kind == Multiplier)
    double total_percent = 0.0;  // signed target percent over the whole interval, e.g. -5.0 for "decrease by 5%"
    double applied_ratio = 1.0;  // cumulative multiplicative ratio already applied so far

    template<class Archive>
    void serialize(Archive& ar) {
        ar(target, attribute, from_value, to_value, start_output_id, start_resolved, total_percent, applied_ratio);
    }
};
CHECK_SERIALIZABLE(RampTarget);

enum class RampLaw { Linear };

inline const char* rampLawToString(RampLaw law) {
    switch (law) {
        case RampLaw::Linear: return "linear";
    }
    throw std::runtime_error("Unknown RampLaw: " + std::to_string(static_cast<int>(law)));
}

/**
 * Value: setGridAction, interpolates an absolute value (RampTarget::from_value/to_value).
 * Multiplier: adjustGridAction, applies incremental DynawoInterface::scaleMultiplierBy deltas (RampTarget::total_percent/applied_ratio).
 */
enum class RampKind { Value, Multiplier };

struct RampParameters {
    double interval_start = 0.0;
    double interval_end = 0.0;
    RampLaw law = RampLaw::Linear;
    RampKind kind = RampKind::Value;

    template<class Archive>
    void serialize(Archive& ar) { ar(interval_start, interval_end, law, kind); }
};
CHECK_SERIALIZABLE(RampParameters);

/**
 * A ramp (`[t0, t1] with law ...`) over adjustGridAction/setGridAction
 * For the sake of simplicity, ramps have been designed to not need to subscribe to live values,
 * so a 'decrease generator input "P" by 15%' uses Dynawo's input_multiplier (via IIDMMapping::buildScaleMultiplierCommand)
 * instead of using the current (output) value (which might not be available).
 */
class RampEvent : public DSLEvent {
    public:
        RampEvent() = default;
        RampEvent(unsigned long id, std::string dsl_text, double generation_time, std::string source, std::optional<unsigned long> parent_event_id,
            std::vector<RampTarget> targets, RampParameters parameters) :
            DSLEvent(id, std::move(dsl_text), generation_time, std::move(source), parent_event_id),
            targets_(std::move(targets)),
            parameters_(std::move(parameters)) {}

        const RampParameters& getParameters() const { return parameters_; }
        bool isTargeting(const std::string& iidm_id, const std::string& attribute) const;

        /**
         * Outputs the ramp reads a starting value from, which the engine keeps subscribed while it is alive.
         */
        std::unordered_set<std::string> startOutputIds() const;

        /**
         * Applies the interpolated (Value) or incremental (Multiplier) update at time `now` for every target
         * (via IIDMMapping + ScenarioHandler::applyScenario(Mode::Execute)).
         * Does nothing if 'now' is not between interval_start and interval_end or if status = Interrupted/Completed
         * Sets status_ = Completed once now >= interval_end.
         */
        void applyTick(ScenarioHandlerInterface& scenario_handler, DSLEngine& engine, double now);

        void interrupt() override {
            if (status_ == DSLStatus::Ready || status_ == DSLStatus::Ongoing) {
                status_ = DSLStatus::Interrupted;
            }
        }

        /**
         * Renders the (possibly partial, if interrupted) ramp as a DSL line, annotated with the
         * actual final time (end_time, which may be < the originally requested interval_end if
         * interrupted) and the actual final value/percentage reached for every target.
         */
        std::string describeInterval(double end_time) const;

        std::string describe() const override;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DSLEvent>(this), targets_, parameters_);
        }

    private:
        std::vector<RampTarget> targets_;
        RampParameters parameters_;
};
SER20_REGISTER_TYPE(RampEvent);
CHECK_SERIALIZABLE(RampEvent);

enum class TriggerKind { When, WhenRearming, After };
enum class RearmState { Armed, Disarmed };

/**
 * A `when` / `when_rearming` / `after ...` trigger.
 * Armed = watching for the condition to become true (ready to fire).
 * Firing moves to Disarmed and increments activation_count_.
 * Only WhenRearming ever goes back from Disarmed to Armed (once the condition goes false again).
 * When/After fire at most once (activation_count_ maxes at 1) and immediately Complete.
 */
class ConditionalEvent : public DSLEvent {
    public:
        ConditionalEvent() = default;
        ConditionalEvent(unsigned long id, std::string dsl_text, double generation_time, std::string source, std::optional<unsigned long> parent_event_id,
                          TriggerKind kind, nlohmann::json condition_expr, std::vector<nlohmann::json> action_payloads,
                          std::optional<std::string> dependency_tag, std::string action_call_source = "") :
            DSLEvent(id, std::move(dsl_text), generation_time, std::move(source), parent_event_id),
            kind_(kind),
            condition_expr_(std::move(condition_expr)),
            action_payloads_(std::move(action_payloads)),
            dependency_tag_(std::move(dependency_tag)),
            action_call_source_(std::move(action_call_source)) {
                for (auto& payload : action_payloads_) assertUntimedPayload(payload);
            }

        TriggerKind getKind() const { return kind_; }
        const std::optional<std::string>& getDependencyTag() const { return dependency_tag_; }
        /**
         * Boolean expression tree (see DSLExprEval.h), re-evaluated by DSLEngine against the
         * live DSLValueCache every tick (only for TriggerKind::When/WhenRearming, unused by TriggerKind::After).
         */
        const nlohmann::json& getConditionExpr() const { return condition_expr_; }
        const std::vector<nlohmann::json>& getActionPayloads() const { return action_payloads_; }
        /**
         * The call triggered by the conditional, when it is a function call, else empty.
         * Eg. when load "01_1" output "P" > 200, isolate("01_1_breaker", "02_1");
         * Returns isolate("01_1_breaker", "02_1")
         */
        const std::string& getActionCallSource() const { return action_call_source_; }

        /**
         * Update the RearmState and fires every payload via ScenarioHandler::applyScenario(Mode::Execute) depending on if 'condition_is_true'.
         */
        bool evaluate(ScenarioHandlerInterface& scenario_handler, bool condition_is_true);

        void interrupt() override {
            if (status_ == DSLStatus::Ready || status_ == DSLStatus::Ongoing) status_ = DSLStatus::Interrupted;
        }

        std::string describe() const override;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DSLEvent>(this), kind_, condition_expr_, action_payloads_, dependency_tag_,
               rearm_state_, activation_count_, action_call_source_);
        }

    private:
        TriggerKind kind_ = TriggerKind::When;
        nlohmann::json condition_expr_;  // boolean expression tree; unused for After
        std::vector<nlohmann::json> action_payloads_;  // what to execute once triggered, one per targeted element
        std::optional<std::string> dependency_tag_;  // for After
        std::string action_call_source_;  // set instead of action_payloads_ when the body is a function call
        RearmState rearm_state_ = RearmState::Armed;
        int activation_count_ = 0;
};
SER20_REGISTER_TYPE(ConditionalEvent);
CHECK_SERIALIZABLE(ConditionalEvent);

/**
 * A function call, expanded into child_event_ids_ at commit time.
 * Nested calls are just another FunctionCallEvent id among a call's children, with their own children.
 */
class FunctionCallEvent : public DSLEvent {
    public:
        FunctionCallEvent() = default;
        FunctionCallEvent(unsigned long id, std::string dsl_text, double generation_time, std::string source, std::optional<unsigned long> parent_event_id,
                          std::vector<unsigned long> child_event_ids) :
            DSLEvent(id, std::move(dsl_text), generation_time, std::move(source), parent_event_id),
            child_event_ids_(std::move(child_event_ids)) {}

        const std::vector<unsigned long>& childEventIds() const { return child_event_ids_; }

        /**
         * Recomputes status_ from the status of each direct child.
         */
        void refreshStatus(const std::unordered_map<unsigned long, std::shared_ptr<DSLEvent>>& registry);

        /**
         * Cascades interrupt() to every child, then marks self Interrupted.
         */
        void interrupt() override;
        /**
         * Same as interrupt, returning every id it actually interrupted, self included.
         */
        std::vector<unsigned long> interruptCascading(const std::unordered_map<unsigned long, std::shared_ptr<DSLEvent>>& registry);
        /**
         * Replace a child event by a new one, used for event edition.
         */
        bool replaceChildId(unsigned long old_id, unsigned long new_id);

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DSLEvent>(this), child_event_ids_);
        }

    private:
        std::vector<unsigned long> child_event_ids_;
};
SER20_REGISTER_TYPE(FunctionCallEvent);
CHECK_SERIALIZABLE(FunctionCallEvent);

/**
 * Aggregates a set of child statuses as:
 * all-Completed -> Completed
 * all-Interrupted -> Interrupted
 * nothing started -> Ready
 * any Ongoing/Completed/Interrupted mix -> Ongoing;
 */
DSLStatus aggregateChildStatus(const std::vector<DSLStatus>& children);

#endif // DSL_EVENT_H
