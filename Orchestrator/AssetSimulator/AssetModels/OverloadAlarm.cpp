/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "OverloadAlarm.h"
#include "AssetModelWithCommunications.h"
#include <Orchestrator.h>


OverloadAlarm::OverloadAlarm(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config) :
    AssetModelWithCommunications(information_flow_model, config) {
    try {
        current_key_ = config["current_key"];
        alarm_key_ = config["alarm_key"];
        max_current_ = config["max_current"];
        max_current_ = abs(max_current_);

    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid OverloadAlarm config: " + std::string(e.what()) + " in:\n" + config.dump());
    }
}

void OverloadAlarm::onUpdate(const std::string& id, const Value& value, double time_received) {
    if (id == current_key_) {
        updateCurrent(value.to_double(), time_received);
    }
}

std::vector<std::string> OverloadAlarm::getSubscriptions() {
    return {current_key_};
}

void OverloadAlarm::updateCurrent(double current, double time) {
    bool armed = abs(current) > max_current_;

    if (armed != armed_) {
        spdlog::trace("OverloadAlarm {}: {} (I = {}, I_max = {})", alarm_key_, armed, current, max_current_);
        armed_ = armed;
        Orchestrator::get().emit(ActualMeasurement(alarm_key_, armed, time, topic_));
        Orchestrator::get().emit(MeasurementSent(alarm_key_, armed, time, destination_, routing_, topic_, tase2_extension_));
    }
}
