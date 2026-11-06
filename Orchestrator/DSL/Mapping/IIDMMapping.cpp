/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "IIDMMapping.h"

#include <stdexcept>
#include <unordered_map>

nlohmann::json IIDMMapping::buildSetCommand(const TargetRef& target, const std::string& attribute,
                                             double value) const {
    return nlohmann::json{
        {"command", target.is_dynamic_model ? "dynamic_model_command" : "iidm_command"},
        {target.is_dynamic_model ? "dynamic_model" : "iidm_id", target.id},
        {"attribute", attribute},
        {"value", value},
    };
}

nlohmann::json IIDMMapping::buildScaleMultiplierCommand(const TargetRef& target, const std::string& attribute,
                                                          double multiplier_increase) const {
    return nlohmann::json{
        {"command", target.is_dynamic_model ? "dynamic_model_scale_multiplier" : "scale_multiplier"},
        {target.is_dynamic_model ? "dynamic_model" : "iidm_id", target.id},
        {"attribute", attribute},
        {"multiplier_increase", multiplier_increase},
    };
}

/**
 * State values of a branch. The grammar only ever reaches 'open' and 'close', the rest being what the Dynawo
 * state variable can otherwise hold.
 */
const std::unordered_map<std::string, double> BRANCH_STATE_VALUES = {
    {"open", 1},
    {"close", 2},
    {"close1", 3},
    {"close2", 4},
    {"close3", 5},
    {"undefined", 6}
};

const std::unordered_map<std::string, std::unordered_map<std::string, double>> CONTROL_VALUE_MAP = {
    {"switch",
        {
            {"open", 1},
            {"close", 2}
        }
    },
    {"line", BRANCH_STATE_VALUES},
    {"transformer", BRANCH_STATE_VALUES},
};

double IIDMMapping::resolveStateValue(const std::string& control_type, const std::string& action) const {
    if (CONTROL_VALUE_MAP.contains(control_type) && CONTROL_VALUE_MAP.at(control_type).contains(action)) {
        return CONTROL_VALUE_MAP.at(control_type).at(action);
    }
    throw std::invalid_argument("No control value mapping for " + control_type + "/" + action);
}
