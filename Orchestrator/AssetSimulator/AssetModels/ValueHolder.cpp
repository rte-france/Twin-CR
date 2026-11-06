/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "ValueHolder.h"
#include "AssetModelWithCommunications.h"
#include "Information.h"
#include "Orchestrator.h"


std::string extractKey(const nlohmann::json::basic_json::value_type& config) {
    try {
        return config["key"];
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid ValueHolder config: " + std::string(e.what()) + " in:\n" + config.dump());
    }
}

ValueHolder::ValueHolder(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config) :
    ValueHolder(information_flow_model, config, extractKey(config)) {}

ValueHolder::ValueHolder(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config, std::string key, std::string class_name) :
    AssetModelWithCommunications(information_flow_model, config), key_(std::move(key)), class_name_(std::move(class_name)) {
    try {
        value_ = config.contains("value") ? Value(config["value"]) : Value(0);
    } catch (const std::invalid_argument& e) {
        throw std::invalid_argument("Invalid " + class_name_ + " config: " + std::string(e.what()) + " in:\n" + config.dump());
    }

    // Publish the initial value at t=0 (skipped on reload (t > 0))
    if (Orchestrator::get().getCurrentTime() <= 0) {
        Orchestrator::get().emitLater(ActualMeasurement(key_, value_, 0, topic_), 0);
        Orchestrator::get().emitLater(
            MeasurementSent(key_, value_, 0, destination_, routing_, topic_, tase2_extension_), 0);
    }
}

void ValueHolder::onUpdate(const std::string& id, const Value& value, double time_received) {
    if (id == key_) {
        // Only emit value if different from previous one (avoids infinite loop)
        if (value != value_) {
            spdlog::trace("{}: {} set to {}", class_name_, id, value);
            value_ = value;
            Orchestrator::get().emit(ActualMeasurement(id, value, time_received, topic_));
            Orchestrator::get().emit(MeasurementSent(id, value, time_received, destination_, routing_, topic_, tase2_extension_));
        }
    }
}

std::vector<std::string> ValueHolder::getSubscriptions() {
    return {key_};
}
