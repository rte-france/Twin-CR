/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "IFLMapping.h"

nlohmann::json IFLMapping::buildNetworkCharacteristicsCommand(const std::vector<std::string>& nodes, const std::vector<std::pair<std::string, std::string>>& links,
                                                              const nlohmann::json& characteristics) const {
    nlohmann::json links_json = nlohmann::json::array();
    for (auto& [from, to] : links) {
        links_json.push_back({{"from", from}, {"to", to}});
    }
    nlohmann::json command{
        {"command", "change_network_characteristics"},
        {"nodes", nodes},
        {"links", links_json},
    };

    if (characteristics.is_object()) {
        for (auto& [key, value] : characteristics.items()) {
            command[key] = value;
        }
    }
    return command;
}
