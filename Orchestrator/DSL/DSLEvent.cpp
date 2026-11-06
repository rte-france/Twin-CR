/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLEvent.h"
#include "../utils/Mode.h"
#include "DSLEngine.h"

#include <fmt/core.h>
#include <spdlog/spdlog.h>

#include <algorithm>

DSLStatus aggregateChildStatus(const std::vector<DSLStatus>& children) {
    bool any_progress = false;
    bool all_completed = true;
    bool all_interrupted = true;

    for (auto s : children) {
        switch (s) {
            case DSLStatus::Completed:   any_progress = true; all_interrupted = false; break;
            case DSLStatus::Ongoing:     any_progress = true; all_completed = false; all_interrupted = false; break;
            case DSLStatus::Interrupted: any_progress = true; all_completed = false; break;
            case DSLStatus::Ready:       all_completed = false; all_interrupted = false; break;
        }
    }
    if (all_completed) return DSLStatus::Completed;  // Including a call with no children at all
    if (all_interrupted) return DSLStatus::Interrupted;
    if (any_progress) return DSLStatus::Ongoing;
    return DSLStatus::Ready;
}

void assertUntimedPayload(const nlohmann::json& payload) {
    if (payload.contains("t_start") || payload.contains("t_start_from_now")) {
        throw std::logic_error("DSL payloads must not carry a scheduling time: " + payload.dump());
    }
}

void ActionEvent::execute(ScenarioHandlerInterface& scenario_handler) {
    if (status_ == DSLStatus::Interrupted) return;
    for (auto& payload : payloads_) {
        scenario_handler.applyScenario(payload, Mode::Execute);
    }
    status_ = DSLStatus::Completed;
}

std::string ActionEvent::describe() const {
    std::string line = fmt::format("at {} seconds, {}", execution_time_, dsl_text_);
    if (tag_) line += fmt::format(" tagged \"{}\"", *tag_);
    line += ";";
    return line;
}

std::unordered_set<std::string> RampEvent::startOutputIds() const {
    std::unordered_set<std::string> ids;
    for (auto& target : targets_) {
        if (!target.start_output_id.empty()) {
            ids.insert(target.start_output_id);
        }
    }
    return ids;
}

bool RampEvent::isTargeting(const std::string& iidm_id, const std::string& attribute) const {
    for (auto& t : targets_) {
        if (t.target.id == iidm_id && t.attribute == attribute) {
            return true;
        }
    }
    return false;
}

void RampEvent::applyTick(ScenarioHandlerInterface& scenario_handler, DSLEngine& engine, double now) {
    if (status_ == DSLStatus::Interrupted || status_ == DSLStatus::Completed) return;
    if (now < parameters_.interval_start) return;

    status_ = DSLStatus::Ongoing;

    double t = std::min(now, parameters_.interval_end);
    double duration = parameters_.interval_end - parameters_.interval_start;
    double fraction = duration > 0 ? (t - parameters_.interval_start) / duration : 1.0;

    switch (parameters_.kind) {
        case RampKind::Multiplier:
            // Dynawo's multiplier is scaled multiplicatively (UpdatableDiscrete/Continuous::scaleMultiplierBy),
            // so per-tick factors must compose multiplicatively too
            for (auto& target : targets_) {
                double target_ratio = 1.0 + (target.total_percent * fraction) / 100.0;
                double tick_factor = target_ratio / target.applied_ratio;
                if (tick_factor != 1.0) {
                    nlohmann::json payload = engine.iidmMapping().buildScaleMultiplierCommand(
                        target.target, target.attribute, tick_factor - 1.0);
                    scenario_handler.applyScenario(payload, Mode::Execute);
                    target.applied_ratio = target_ratio;
                }
            }
            break;
        case RampKind::Value:
            for (auto& target : targets_) {
                if (!target.start_resolved) {
                    // The subscription was only set up when the statement was committed, so the first measurement can land a period later.
                    // Skip the tick rather than ramp from nothing; the fraction keeps running off the interval, so the ramp catches up once a value arrives.
                    auto current = engine.currentValue(target.start_output_id);
                    if (current) {
                        target.from_value = *current;
                        target.start_resolved = true;
                    } else if (t < parameters_.interval_end) {
                        continue;
                    } else {
                        // The interval is over and nothing ever arrived
                        // This should never occur except for very short ramps, so only apply the final value
                        spdlog::warn("Ramp {} never read {}, so {} goes straight to its final value {}", id_, target.start_output_id, target.target.id, target.to_value);
                        target.from_value = target.to_value;
                        target.start_resolved = true;
                    }
                }
                double value = target.from_value + fraction * (target.to_value - target.from_value);
                nlohmann::json payload = engine.iidmMapping().buildSetCommand(target.target, target.attribute, value);
                scenario_handler.applyScenario(payload, Mode::Execute);
            }
            break;
    }

    if (t >= parameters_.interval_end) {
        status_ = DSLStatus::Completed;
    }
}

std::string RampEvent::describe() const {
    std::string line = fmt::format("at [{} seconds, {} seconds] with law {}, {}",
                                    parameters_.interval_start, parameters_.interval_end, rampLawToString(parameters_.law), dsl_text_);
    if (tag_) line += fmt::format(" tagged \"{}\"", *tag_);
    line += ";";
    return line;
}

std::string RampEvent::describeInterval(double end_time) const {
    double actual_end = std::min(end_time, parameters_.interval_end);
    double duration = parameters_.interval_end - parameters_.interval_start;
    double fraction = duration > 0 ? (actual_end - parameters_.interval_start) / duration : 1.0;

    std::string line = fmt::format("at [{} seconds, {} seconds] with law {}, {}",
                                    parameters_.interval_start, actual_end, rampLawToString(parameters_.law), dsl_text_);
    if (tag_) line += fmt::format(" tagged \"{}\"", *tag_);
    line += ";";

    line += fmt::format(" // reached at t={}:", actual_end);
    switch (parameters_.kind) {
        case RampKind::Multiplier:
            for (auto& target : targets_) {
                line += fmt::format(" {}={:+.2f}%", target.target.id, target.total_percent * fraction);
            }
            break;
        case RampKind::Value:
            for (auto& target : targets_) {
                double reached = target.from_value + fraction * (target.to_value - target.from_value);
                double percent = target.from_value != 0.0 ? (reached - target.from_value) / target.from_value * 100.0 : 0.0;
                line += fmt::format(" {}={:.6g} ({:+.2f}%)", target.target.id, reached, percent);
            }
            break;
    }
    return line;
}

bool ConditionalEvent::evaluate(ScenarioHandlerInterface& scenario_handler, bool condition_is_true) {
    if (status_ == DSLStatus::Interrupted || status_ == DSLStatus::Completed) return false;

    switch (rearm_state_) {
        case RearmState::Armed:
            if (condition_is_true) {
                for (auto& payload : action_payloads_) {
                    scenario_handler.applyScenario(payload, Mode::Execute);
                }
                activation_count_++;
                rearm_state_ = RearmState::Disarmed;
                if (kind_ == TriggerKind::WhenRearming) {
                    status_ = DSLStatus::Ongoing;
                } else {
                    status_ = DSLStatus::Completed;
                }
                return true;
            }
            break;
        case RearmState::Disarmed:
            if (kind_ == TriggerKind::WhenRearming && !condition_is_true) {
                rearm_state_ = RearmState::Armed;
            }
            break;
    }
    return false;
}

std::string ConditionalEvent::describe() const {
    std::string line = dsl_text_;
    if (tag_) line += fmt::format(" tagged \"{}\"", *tag_);
    line += ";";
    return line;
}

void FunctionCallEvent::refreshStatus(const std::unordered_map<unsigned long, std::shared_ptr<DSLEvent>>& registry) {
    if (status_ == DSLStatus::Interrupted) return;
    std::vector<DSLStatus> child_statuses;
    child_statuses.reserve(child_event_ids_.size());
    for (auto& id : child_event_ids_) {
        if (registry.contains(id)) {
            child_statuses.push_back(registry.at(id)->getStatus());
        } else {
            // Child deleted from the registry because it has been interrupted
            child_statuses.push_back(DSLStatus::Interrupted);
        }
    }
    status_ = aggregateChildStatus(child_statuses);
}

bool FunctionCallEvent::replaceChildId(unsigned long old_id, unsigned long new_id) {
    auto it = std::find(child_event_ids_.begin(), child_event_ids_.end(), old_id);
    if (it == child_event_ids_.end()) return false;
    *it = new_id;
    return true;
}

void FunctionCallEvent::interrupt() {
    if (status_ == DSLStatus::Ready || status_ == DSLStatus::Ongoing) {
        status_ = DSLStatus::Interrupted;
    }
}

std::vector<unsigned long> FunctionCallEvent::interruptCascading(const std::unordered_map<unsigned long, std::shared_ptr<DSLEvent>>& registry) {
    std::vector<unsigned long> interrupted;
    for (auto& id : child_event_ids_) {
        if (!registry.contains(id)) continue;
        auto& child = registry.at(id);
        if (child->getStatus() == DSLStatus::Ready || child->getStatus() == DSLStatus::Ongoing) {
            if (auto nested = std::dynamic_pointer_cast<FunctionCallEvent>(child)) {
                auto nested_ids = nested->interruptCascading(registry);
                interrupted.insert(interrupted.end(), nested_ids.begin(), nested_ids.end());
            }
            child->interrupt();
            interrupted.push_back(id);
        }
    }
    interrupt();
    interrupted.push_back(getId());
    return interrupted;
}
