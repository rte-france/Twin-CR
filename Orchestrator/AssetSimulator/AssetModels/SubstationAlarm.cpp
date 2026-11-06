/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "SubstationAlarm.h"


std::string computeKey(const nlohmann::json::basic_json::value_type& config) {
    try {
        std::string substation_name = config["substation_name"];
        return "operator_in_" + substation_name;
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid SubstationAlarm config: " + std::string(e.what()) + " in:\n" + config.dump());
    }
}

SubstationAlarm::SubstationAlarm(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config) :
    ValueHolder(information_flow_model, config, computeKey(config), "SubstationAlarm") {}
