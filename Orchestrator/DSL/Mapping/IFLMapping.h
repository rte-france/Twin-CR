/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef IFL_MAPPING_H
#define IFL_MAPPING_H

#include <nlohmann/json.hpp>

#include <string>
#include <utility>
#include <vector>

/**
 * Translates a resolved `networkAction` into a JSON payload ScenarioHandler::applyScenario accepts.
 */
class IFLMapping {
    public:
        nlohmann::json buildNetworkCharacteristicsCommand(const std::vector<std::string>& nodes, const std::vector<std::pair<std::string, std::string>>& links,
                                                          const nlohmann::json& characteristics) const;
};

#endif // IFL_MAPPING_H
