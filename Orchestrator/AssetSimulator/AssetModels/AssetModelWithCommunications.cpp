/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "AssetModelWithCommunications.h"


AssetModelWithCommunications::AssetModelWithCommunications(const InformationFlowModel& information_flow_model, const nlohmann::json::basic_json::value_type& config) {
    try {
        location_ = config["location"];
        destination_ = config["destination"];
        topic_ = config["topic"];
        routing_ = information_flow_model.getPath(location_, destination_);
        tase2_extension_ = tase2::parseTase2Extension(config);
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid AssetModelWithCommunications config: " + std::string(e.what()) + " in:\n" + config.dump());
    }
}
