/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef SCENARIO_HANDLER_INTERFACE_H
#define SCENARIO_HANDLER_INTERFACE_H

#include "Mode.h"

#include <nlohmann/json.hpp>

#include <string>
#include <vector>

/**
 * Interface of the ScenarioHandler. Currently implemented by the ScenarioHandler itself and by a mock (testing/RecordingScenarioHandler.h)
 */
class ScenarioHandlerInterface {
    public:
        virtual ~ScenarioHandlerInterface() = default;
        virtual nlohmann::json applyScenario(const nlohmann::json& scenario, Mode mode) = 0;

        virtual std::vector<std::string> listNodes() = 0;
        virtual std::vector<std::string> listDestinations(const std::string& source) = 0;
};

#endif // SCENARIO_HANDLER_INTERFACE_H
