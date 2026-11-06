/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef GAME_MASTER_INTERFACE_H
#define GAME_MASTER_INTERFACE_H

#include "ClickHouseLogger.h"
#include "Information.h"
#include "ScenarioHandler.h"

#include <nats.h>

/**
 * Class responsible for implementing the control signals sent from the Game Master
 */
class GameMasterInterface {
    public:
        GameMasterInterface(ScenarioHandler& scenario_handler, ClickHouseLogger& logger);

        ~GameMasterInterface();

        /**
         * Handle messages sent from the Game Master
         * Returns either
         * - "OK" if message was correctly handled
         * - A return string if requested in the original message (e.g. for the get_link_characteristics command)
         * - An error message (if handling failed)
         */
        std::string handleMessage(const natsMsg* nats_message);

    private:
        void handleControl(const nlohmann::json::basic_json::value_type& j);

        ClickHouseLogger& logger_;
        ScenarioHandler& scenario_handler_;
        natsConnection* nats_connection_;
        natsSubscription* nats_subscription_;
};

#endif // GAME_MASTER_INTERFACE_H
