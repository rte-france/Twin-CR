/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "HmiInterface.h"
#include "Credentials.h"
#include "Information.h"
#include "NatsHelper.h"
#include "Orchestrator.h"
#include "../utils/TomlExtension.h"

#include "mimalloc.h"
#include "nats.h"
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

HMIInterface::HMIInterface(InformationFlowModel& information_flow_model, ScenarioHandler& scenario_handler, ClickHouseLogger& logger) :
information_flow_model_(information_flow_model),
scenario_handler_(scenario_handler),
logger_(logger) {
    auto& working_dir = Orchestrator::get().getWorkingDir();
    auto& config = Orchestrator::get().getConfig();
    location_ = get_or_throw<std::string>(config, {"hmi", "location"});

    std::filesystem::path scada_inputs_file = working_dir / get_or_throw<std::string>(config, {"input_files", "scada_inputs_file"});
    auto scada_inputs = nlohmann::json::parse(std::ifstream(scada_inputs_file));
    for (auto scada_input : scada_inputs) {
        try {
            std::string id = scada_input["id"];
            std::string destination = scada_input["destination"];
            auto routing = information_flow_model_.getPath(location_, destination);
            auto signalisation_data = SignalisationData(id, destination, routing);

            id_to_signalisation_data_[id] = signalisation_data;
            if (scada_input.contains("tase2") && scada_input["tase2"].is_string()) {
                tase2_id_to_id_[scada_input["tase2"]] = id;
            }
        } catch (const nlohmann::detail::type_error& e) {
            throw std::invalid_argument("Invalid scada input: " + std::string(e.what()) + " in:\n" + scada_input.dump());
        }
    }
    scada_inputs.clear();
    mi_collect(true);

    // Connect to NATS server
    nats_connection_ = nullptr;
    natsStatus s = natsConnection_ConnectTo(&nats_connection_, Credentials::get().getNatsURL());
    if (s != NATS_OK) {
       throw std::runtime_error("Connect failed: " + std::string(natsStatus_GetText(s)));
    }

    nats_subscription_ = nullptr;
    natsSubscribe(nats_connection_, nats_subscription_, "HMIControl.>", [this](const natsMsg* msg) {
        return handleMessage(msg);
    });
}

HMIInterface::~HMIInterface() {
    natsSubscription_Destroy(nats_subscription_);
    natsConnection_Destroy(nats_connection_);
}

std::string HMIInterface::handleMessage(const natsMsg* nats_message) {
    std::string message = natsMsg_GetData(nats_message);
    std::string topic = natsMsg_GetSubject(nats_message);

    std::string source;  // Topic is used to define the source, e.g. "HMIControl.automaton" --> automaton sent the message
    size_t pos = topic.find('.');
    if (pos == std::string::npos) {
        source = "";
    } else {
        source = topic.substr(pos + 1);
    }

    spdlog::info("HMI interface received: {} from {}", message, source);
    logger_.logSCADACommand(Orchestrator::get().getCurrentTime(), source, message);

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

        } else {
            reply.update(handleControl(j));
        }

    } catch (const nlohmann::json::parse_error& e) {
        reply["status"] = "JSON parse error: " + std::string(e.what());
    } catch (const std::invalid_argument &e) {
        reply["status"] = e.what();
    } catch (const nlohmann::detail::type_error& e) {
        reply["status"] = "Invalid message: " + std::string(e.what()) + " in: " + message;
    } catch (const nlohmann::detail::out_of_range& e) {
        reply["status"] = "Invalid message: " + std::string(e.what()) + " in: " + message;
    }

    spdlog::info("HMI interface replied with \"{}\"", reply.dump(4));
    return reply.dump(4);
}

nlohmann::json HMIInterface::handleControl(const nlohmann::json::basic_json::value_type& j) {
    auto tase2_data = tase2::parseTase2Extension(j);

    std::string id;
    if (j.contains("id")) {
        id = j["id"];
    } else if (tase2_data.has_value()) {
        if (!tase2_id_to_id_.contains(tase2_data->tase2_id)) {
            throw std::invalid_argument("No id defined for tase2_id " + tase2_data->tase2_id);
        }
        id = tase2_id_to_id_.at(tase2_data->tase2_id);
    } else {
        throw std::invalid_argument("Control message must specify at least \"id\" or \"tase2\"");
    }

    Value value(j["value"]);

    ControlFlags flags;
    flags.with_fast_TS = j.value("with_fast_TS", false);
    flags.real_time_critical = j.value("real_time_critical", false);

    if (!id_to_signalisation_data_.contains(id)) {
        throw std::invalid_argument("No inputs_routing_ defined for " + id + ", control signal will not be send");
    }

    const auto& signalisation_data = id_to_signalisation_data_.at(id);
    const std::string& destination = signalisation_data.destination;
    const auto& routing = signalisation_data.route;
    std::string topic = "HMI";
    int64_t control_uid = information_flow_model_.nextControlUid();

    if (flags.real_time_critical) {
        // Bypass the event queue (which may lag behind real time): timestamp from the real-time clock, and let
        // the IFL compute the control and its acknowledgement from this thread
        // Return the round-trip time delay and let the caller the responsibility to implement the delay
        double clock_time = Orchestrator::get().getClockTime();
        spdlog::debug("HMI interface creating real-time critical control signal: {} : {} at t={}", id, value, clock_time);
        auto acknowledgement = information_flow_model_.handleRealTimeCriticalControl(
            ControlSent(id, value, clock_time, destination, routing, topic, tase2_data, control_uid, flags));
        if (!acknowledgement.has_value()) {
            return {{"control_uid", control_uid}, {"acknowledgement", nullptr}};
        }
        nlohmann::json j_acknowledgement = {
            {"control_uid", acknowledgement->control_uid},
            {"id", acknowledgement->id},
            {"value", acknowledgement->value.to_json()},
            {"source", destination},
            {"destination", acknowledgement->destination},
            {"control_time_sent", acknowledgement->control_time_sent},
            {"time_sent", acknowledgement->time_sent},
            {"time_received", acknowledgement->time_received},
            {"delay", acknowledgement->time_received - acknowledgement->control_time_sent},  // Round trip time delay
        };
        return {{"control_uid", control_uid}, {"acknowledgement", std::move(j_acknowledgement)}};
    }

    double current_time = Orchestrator::get().getCurrentTime();
    spdlog::debug("HMI interface creating control signal: {} : {}", id, value);
    // Direct event emission is not thread-safe, so we go through the main event queue with emit<X>Later instead
    Orchestrator::get().emitLater(
        ControlSent(id, value, current_time, destination, routing, topic, tase2_data, control_uid, flags),
        current_time
    );
    return {{"control_uid", control_uid}};
}
