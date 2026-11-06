/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "GameMasterInterface.h"
#include "Credentials.h"
#include "NatsHelper.h"
#include "Orchestrator.h"
#include "nats.h"

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <stdexcept>

GameMasterInterface::GameMasterInterface(ScenarioHandler& scenario_handler, ClickHouseLogger& logger) :
logger_(logger),
scenario_handler_(scenario_handler) {
    // Connect to NATS server
    nats_connection_ = nullptr;
    natsStatus s = natsConnection_ConnectTo(&nats_connection_, Credentials::get().getNatsURL());
    if (s != NATS_OK) {
       throw std::runtime_error("Connect failed: " + std::string(natsStatus_GetText(s)));
    }

    // Setup subscription to GameMasterControl nats topic
    nats_subscription_ = nullptr;
    natsSubscribe(nats_connection_, nats_subscription_, "GameMasterControl.>", [this](const natsMsg* msg) {
        return handleMessage(msg);
    });
}

GameMasterInterface::~GameMasterInterface() {
    natsSubscription_Destroy(nats_subscription_);
    natsConnection_Destroy(nats_connection_);
}

std::string GameMasterInterface::handleMessage(const natsMsg* nats_message) {
    std::string message = natsMsg_GetData(nats_message);
    std::string topic = natsMsg_GetSubject(nats_message);

    std::string source;  // Topic is used to define the source, e.g. "GameMasterControl.Trainer" --> Trainer sent the message
    size_t pos = topic.find('.');
    if (pos == std::string::npos) {
        source = "";
    } else {
        source = topic.substr(pos + 1);
    }

    spdlog::trace("Game master interface received: {} from {}", message, source);
    logger_.logGameMasterCommand(Orchestrator::get().getCurrentTime(), source, message);

    nlohmann::json reply;
    reply["status"] = "OK";
    try {
        auto j = nlohmann::json::parse(message);
        if (!j.is_object()) {
            reply["status"] = "Message should be a json dict, not array";

        // Message formatted as scenario
        } else if (j.contains("command")) {
            // Validate scenario JSON
            scenario_handler_.applyScenario(j, Mode::Validate);
            // Launch scenario if valid
            // This separation of validation and execution is necessary because execution will only throw when we reach "t_start",
            // and we want to reply directly if the scenario is not valid
            reply = scenario_handler_.applyScenario(j, Mode::Execute);

        // Message formatted a ActualControl
        } else if (j.contains("id") && j.contains("value")) {
            handleControl(j);

        } else {
            throw std::invalid_argument("Message should contain either a 'command' field, or an 'id' and 'value'");
        }

    } catch (const nlohmann::json::parse_error& e) {
        reply["status"] = "JSON parse error: " + std::string(e.what());
    } catch (const nlohmann::detail::type_error& e) {
        reply["status"] = "Invalid message: " + std::string(e.what()) + " in: " + message;
    } catch (const std::invalid_argument &e) {
        reply["status"] = e.what();
    }

    if (reply["status"] == "OK") {
        spdlog::trace("Game master replied with {}", reply.dump(4));
    } else {
        spdlog::info("Game master replied with {}", reply.dump(4));
    }

    return reply.dump(4);
}

void GameMasterInterface::handleControl(const nlohmann::json::basic_json::value_type& j) {
    const std::string& id = j["id"];
    Value value(j["value"]);

    spdlog::debug("Game master creating control signal: {} : {}", id, value);

    std::string topic = "GameMaster";
    double current_time = Orchestrator::get().getCurrentTime();
    // Direct event emission is not thread-safe, so we go through the main event queue with emit<X>Later instead
    Orchestrator::get().emitLater(
        ActualControl(id, value, current_time, topic),
        current_time
    );
}
