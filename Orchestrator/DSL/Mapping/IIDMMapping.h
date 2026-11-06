/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef IIDM_MAPPING_H
#define IIDM_MAPPING_H

#include <nlohmann/json.hpp>

#include <string>

/**
 * What a resolved action acts on: an IIDM equipment id, or a purely dynamic model.
 * Impact what kind of payload of ScenarioHandler is usd
 */
struct TargetRef {
    std::string id;
    bool is_dynamic_model = false;

    template<class Archive>
    void serialize(Archive& ar) {
        ar(id, is_dynamic_model);
    }
};

/**
 * Translates already-resolved DSL constructs (a target, an attribute, a value) into a JSON payloads ScenarioHandler::applyScenario accepts.
 */
class IIDMMapping {
    public:
        nlohmann::json buildSetCommand(const TargetRef& target, const std::string& attribute, double value) const;

        nlohmann::json buildScaleMultiplierCommand(const TargetRef& target, const std::string& attribute, double multiplier_increase) const;

        /**
         * Resolves "open"/"close" for a switch, line or transformer into the numeric "state" value.
         */
        double resolveStateValue(const std::string& control_type, const std::string& action) const;
};

#endif // IIDM_MAPPING_H
