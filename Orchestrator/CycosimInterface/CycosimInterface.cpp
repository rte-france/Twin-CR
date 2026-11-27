/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "CycosimInterface.h"
#include "CycosimSocket.h"
#include "Information.h"
#include "Orchestrator.h"

#include <fmt/core.h>
#include <spdlog/spdlog.h>
#include <stdexcept>
#include <string>

CycosimInterface::CycosimInterface(nlohmann::json cycosim_config, InformationFlowModel& information_flow_model) :
config_(cycosim_config),
period_(config_.at("cycosim_period")),
forward_set_(config_.at("forward")),
cycosim_nodes_(config_.at("cycosim_nodes")),
socket_(CycosimSocket(config_.at("zmq_req_address"))),
information_flow_model_(information_flow_model) {
    Orchestrator::get().subscribeTo<ActualMeasurement, &CycosimInterface::onActualMeasurement>(this);
    Orchestrator::get().subscribeTo<CycosimMeasurementReceived, &CycosimInterface::sendMeasurement>(this);
    Orchestrator::get().subscribeTo<CycosimControlReceived, &CycosimInterface::sendControl>(this);
    Orchestrator::get().subscribeTo<CycosimAcknowledgementReceived, &CycosimInterface::sendAcknowledgement>(this);

    if (!config_.contains("topic_mapping")) {
        spdlog::warn("CycosimInterface: No topic_mapping found in the cycosim config, CycosimInterface will not be able to receive non-empty messages");

    } else if (!config_.at("topic_mapping").is_object()) {
        throw std::invalid_argument(fmt::format("CycosimInterface: topic_mapping must be an object, got: {}", config_.at("topic_mapping").type_name()));
    } else {
        for (const auto& [topic, ids] : config_.at("topic_mapping").items()) {
            if (!ids.is_array()) {
                throw std::invalid_argument(fmt::format("CycosimInterface: topic_mapping entry '{}' must be an array, got: {}", topic, ids.type_name()));
            }
            for (const auto& id : ids) {
                if (!id.is_string()) {
                    throw std::invalid_argument(fmt::format("CycosimInterface: topic_mapping entry '{}' contains non-string id: {}", topic, id.dump()));
                }
                topic_map_[id.get<std::string>()] = topic;
            }
        }
    }

    init_seconds_since_epoch_ = std::chrono::duration_cast<std::chrono::duration<double>>(Orchestrator::get().getInitialClockTime().time_since_epoch()).count();
    message_string_buffer_.reserve(256);

    // Schedule synchronization events with Cycosim.
    Orchestrator::get().scheduleEvent(0, makeCallback<&CycosimInterface::initCycosim>(this));  // Schedule for t=0 to keep constructor fast
    Orchestrator::get().scheduleEvent(period_, makeCallback<&CycosimInterface::goToNextTimeStep>(this), Event::Order::CycosimStep);
}

CycosimInterface::~CycosimInterface() {
    try {
        nlohmann::json stop;
        stop["type"] = "stop";
        socket_.send(stop);
        if (!socket_.attempt_receive(5000).has_value()) {
            spdlog::warn("CycosimInterface: Timed out waiting for stop ack");
        }
        spdlog::debug("CycosimInterface: Sent stop signal to Cycosim");
    } catch (const std::exception& e) {
        spdlog::warn("CycosimInterface: Failed to send stop to Cycosim: {}", e.what());
    }
}

void CycosimInterface::initCycosim() {
    spdlog::debug("CycosimInterface: Sending start signal to Cycosim...");
    nlohmann::json start;
    start["type"] = "start";
    start["next_sync_time"] = period_;
    socket_.send(start);

    std::optional<nlohmann::json> ack = socket_.receive();
    if (!ack.has_value()) {
        return;  // SignalHandler::gotExitSignal()
    }
    if (ack.value()["type"] != "ack") {
        throw std::runtime_error("CycosimInterface: Expected ack, got: " + ack.value().dump());
    }
    spdlog::info("CycosimInterface: Cycosim start acknowledged, proceeding");
}

void CycosimInterface::goToNextTimeStep() {
    // Use a time-based synchronisation mechanism and not event-based as it could lead to >1M synchronisations per second.
    // Measurements arriving between syncs are buffered in to_publish_ and sent in bulk.
    tick_index_++;
    next_sync_time_ = start_time_ + tick_index_ * period_;

    sendEventsToCycosim();
    receiveMessagesFromCycosim();

    Orchestrator::get().scheduleEvent(next_sync_time_, makeCallback<&CycosimInterface::goToNextTimeStep>(this), Event::Order::CycosimStep);
}

void CycosimInterface::parseCycosimMessage(nlohmann::json message) {
    if (!message.contains("type")) {
        spdlog::warn("Received message without type: {}", message.dump());
        return;
    }

    // Handle empty messages first (used for synchronization when no data to send)
    if (message["type"] == "empty") {
        spdlog::debug("CycosimReceiver: Received empty sync message");
        return;
    }

    double current_time = Orchestrator::get().getCurrentTime();
    std::string id;
    Value value;
    try {
        id = message["id"];
        value = Value(message["value"]);
    } catch (const nlohmann::json::type_error& e) {
        spdlog::warn("Received message without id: {}", message.dump());
        return;
    } catch (const std::invalid_argument& e) {
        spdlog::warn("Could not parse message value, msg: {}\nError: ", message.dump(), e.what());
        return;
    }

    std::string topic;
    if (topic_map_.contains(id)) {
        topic = topic_map_.at(id);
    } else {
        throw std::runtime_error(fmt::format("No topic specified for {}", id));
    }

    if (message["type"] == "actualControl") {
        Orchestrator::get().emit(ActualControl(id, value, current_time, topic));
    }

    std::string source_twincr = message.value("source", "");
    std::string destination_twincr = message.value("destination", "");

    if (source_twincr.empty() || destination_twincr.empty()) {
        spdlog::warn("Received message with empty source or destination: {}", message.dump());
        return;
    }
    std::vector<graaf::vertex_id_t> path;
    try {
        path = information_flow_model_.getPath(source_twincr, destination_twincr);
    } catch (const std::invalid_argument& e) {
        spdlog::warn(e.what());
    }

    auto tase2_data = tase2::parseTase2Extension(message);

    if (message["type"] == "MeasurementSent") {
        auto ts = MeasurementSent(id, value, current_time, destination_twincr, path, topic, std::move(tase2_data));
        Orchestrator::get().emit(ts);
    } else if (message["type"] == "ControlSent") {
        ControlFlags flags;
        flags.with_fast_TS = message.value("with_fast_TS", false);
        flags.real_time_critical = message.value("real_time_critical", false);
        auto tc = ControlSent(id, value, current_time, destination_twincr, path, topic, std::move(tase2_data), information_flow_model_.nextControlUid(), flags);
        if (flags.real_time_critical) {
            // The acknowledgement is computed at once and queued for the next sync, its delay incorporated in its time
            auto acknowledgement = information_flow_model_.handleRealTimeCriticalControl(tc);
            if (acknowledgement.has_value()) {
                queueAcknowledgement(*acknowledgement, source_twincr);
            }
        } else {
            Orchestrator::get().emit(tc);
        }
    } else {
        spdlog::warn("Received message with unknown type: {}", message.dump());
    }
}

void CycosimInterface::receiveMessagesFromCycosim() {
    std::optional<nlohmann::json> batch = socket_.receive();
    if (!batch.has_value()) {
        return;
    }
    for (const auto& message : batch.value().at("events")) {
        parseCycosimMessage(message);
    }
}

void CycosimInterface::sendEventsToCycosim() {
    nlohmann::json reply;
    reply["type"] = "sync";
    reply["next_sync_time"] = next_sync_time_;
    reply["events"] = nlohmann::json::array();

    while (!to_publish_.empty()) {
        reply["events"].push_back(to_publish_.front());
        to_publish_.pop_front();
    }

    spdlog::trace("CycosimInterface: Sending {} event(s), next_sync_time={}", reply["events"].size(), next_sync_time_);
    socket_.send(reply);
}

void CycosimInterface::onActualMeasurement(const ActualMeasurement& info) {
    // Check if this measurement should be forwarded to Cycosim
    if (forward_set_.contains(info.id)) {
        spdlog::debug("CycosimInterface: Forwarding ActualMeasurement {} = {} to Cycosim nodes", info.id, info.value.to_string());

        sendActualMeasurement(info);
    }
}

void CycosimInterface::sendActualMeasurement(const ActualMeasurement& info) {
    nlohmann::json msg;
    msg["id"] = info.id;
    msg["value"] = info.value.to_json();
    msg["time"] = info.time;
    msg["type"] = "physicalMeasurement";

    spdlog::trace("CycosimInterface: Queuing ActualMeasurement - source='{}', destination='none', value={}, type='physicalMeasurement'", info.id, info.value);

    to_publish_.push_back(msg);
}

void CycosimInterface::sendMeasurement(const CycosimMeasurementReceived& info) {
    spdlog::trace(
        "CycosimInterface: Queuing MeasurementSent - source='{}', destination='{}', value={}, type='MeasurementReceived'",
        info.id, info.destination, info.value
    );

    message_string_buffer_.clear();
    fmt::format_to(std::back_inserter(message_string_buffer_),
R"({{
    "id":"{}",
    "source":"{}",
    "destination":"{}",
    "value":{},
    "time":{},
    "type":"MeasurementReceived")", info.id, info.source, info.destination, info.value, info.time_received);

    if (info.tase2_data.has_value()) {
        appendTase2Field(message_string_buffer_, info.tase2_data->tase2_id, info.value, info.time_received, init_seconds_since_epoch_, info.tase2_data->cause, info.tase2_data->validity, info.tase2_data->operator_blocked, info.tase2_data->signalisation_type);
    }
    fmt::format_to(std::back_inserter(message_string_buffer_), "}}");

    to_publish_.push_back(nlohmann::json::parse(std::string_view(message_string_buffer_.data(), message_string_buffer_.size())));
}

void CycosimInterface::sendControl(const CycosimControlReceived& info) {
    spdlog::trace(
        "CycosimInterface: Queuing ControlSent - source='{}', destination='{}', value={}, type='ControlReceived'",
        info.id, info.destination, info.value);

    message_string_buffer_.clear();
    fmt::format_to(std::back_inserter(message_string_buffer_),
R"({{
    "id":"{}",
    "source":"{}",
    "destination":"{}",
    "value":{},
    "time":{},
    "type":"ControlReceived")", info.id, info.source, info.destination, info.value, info.time_received);

    if (info.tase2_data.has_value()) {
        appendTase2Field(message_string_buffer_, info.tase2_data->tase2_id, info.value, info.time_received, init_seconds_since_epoch_, info.tase2_data->cause, info.tase2_data->validity, info.tase2_data->operator_blocked, info.tase2_data->signalisation_type);
    }
    fmt::format_to(std::back_inserter(message_string_buffer_), "}}");

    to_publish_.push_back(nlohmann::json::parse(std::string_view(message_string_buffer_.data(), message_string_buffer_.size())));
}

void CycosimInterface::sendAcknowledgement(const CycosimAcknowledgementReceived& info) {
    if (info.flags.real_time_critical) {
        return;  // Already queued for Cycosim when the control was sent
    }
    queueAcknowledgement(info, info.source);
}

void CycosimInterface::queueAcknowledgement(const AcknowledgementReceived& info, const std::string& source) {
    spdlog::trace(
        "CycosimInterface: Queuing AcknowledgementReceived - id='{}', destination='{}', value={}",
        info.id, info.destination, info.value);

    nlohmann::json msg;
    msg["id"] = info.id;
    msg["source"] = source;
    msg["destination"] = info.destination;
    msg["value"] = info.value.to_json();
    msg["control_uid"] = info.control_uid;
    msg["control_time_sent"] = info.control_time_sent;
    msg["time_sent"] = info.time_sent;
    msg["time"] = info.time_received;
    msg["with_fast_TS"] = info.flags.with_fast_TS;
    msg["real_time_critical"] = info.flags.real_time_critical;
    msg["type"] = "AcknowledgementReceived";

    to_publish_.push_back(std::move(msg));
}
