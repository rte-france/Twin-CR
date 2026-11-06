/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef HMI_INTERFACE_H
#define HMI_INTERFACE_H

#include "ClickHouseLogger.h"
#include "InformationFlowModel.h"
#include "ScenarioHandler.h"

#include <nats.h>
#include <toml++/toml.h>
#include <unordered_map>

struct SignalisationData {
    std::string id;
    std::string destination;
    std::vector<graaf::vertex_id_t> route;
};

/**
 * Class responsible for implementing the control signals sent from the HMI (human-machine interface)
 */
class HMIInterface {
    public:
        HMIInterface(const InformationFlowModel& information_flow_model, ScenarioHandler& scenario_handler, ClickHouseLogger& logger);

        ~HMIInterface();

        /**
         * Handle messages sent from the HMI
         * Returns "OK" if message was correctly handled, else, returns an error message
         */
        std::string handleMessage(const natsMsg* nats_message);

    private:
        void handleControl(const nlohmann::json::basic_json::value_type& j);

        const InformationFlowModel& information_flow_model_;
        ScenarioHandler& scenario_handler_;
        ClickHouseLogger& logger_;
        std::string location_;
        natsConnection* nats_connection_;
        natsSubscription* nats_subscription_;
        std::unordered_map<std::string, SignalisationData> id_to_signalisation_data_;
        std::unordered_map<std::string, std::string> tase2_id_to_id_;
};

#endif // HMI_INTERFACE_H
