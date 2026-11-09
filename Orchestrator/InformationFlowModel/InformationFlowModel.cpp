/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "InformationFlowModel.h"
#include "ClickHouseLogger.h"
#include "Orchestrator.h"
#include "../utils/TomlExtension.h"

#include <graaflib/graph.h>
#include <memory>
#include <sstream>


InformationFlowModel::InformationFlowModel(bool with_subscriptions, ClickHouseLogger& logger, std::optional<nlohmann::json> cycosim_config):
logger_(logger) {
    const auto& working_dir = Orchestrator::get().getWorkingDir();
    const auto& config = Orchestrator::get().getConfig();

    std::filesystem::path cyber_config_file = working_dir / get_or_throw<std::string>(config, {"input_files", "cyber_config_file"});
    std::string scada_location = get_or_throw<std::string>(config, {"hmi", "location"});

    network_graph_ = std::make_unique<NetworkGraph>(cyber_config_file, scada_location, cycosim_config);

    if (with_subscriptions) {
        initSubscriptions();
    }
}

InformationFlowModel::InformationFlowModel(ClickHouseLogger& logger, double time): logger_(logger) {
    auto string_buf = logger_.loadDump("InformationFlowModel", time);
    std::istringstream ss(string_buf);
    ser20::BinaryInputArchive ar(ss);
    ar(*this);

    initSubscriptions();
}

void InformationFlowModel::initSubscriptions() {
    Orchestrator::get().subscribeTo<MeasurementSent, &InformationFlowModel::handleMeasurementSent>(this);
    Orchestrator::get().subscribeTo<ControlSent, &InformationFlowModel::handleControlSent>(this);
    Orchestrator::get().subscribeTo<ControlReceived, &InformationFlowModel::onControlReceived>(this);
    Orchestrator::get().subscribeTo<AcknowledgementSent, &InformationFlowModel::handleAcknowledgementSent>(this);
    Orchestrator::get().subscribeTo<DumpStateEvent, &InformationFlowModel::handleDumpStateEvent>(this);
}

void InformationFlowModel::dumpState(const std::filesystem::path dump_path){
    std::ofstream os(dump_path, std::ios::binary);
    ser20::BinaryOutputArchive archive(os);
    archive(*this);
}

void InformationFlowModel::handleMeasurementSent(const MeasurementSent& info) {
    // Copy info in a MeasurementReceived event (with time_received=current_time)
    auto info_received = MeasurementReceived(info, Orchestrator::get().getCurrentTime());
    // Apply delay, drop and corruption functions on the created MeasurementReceived event (possibly modifying info.time_received and info.value)
    bool dropped;
    {
        std::lock_guard<std::recursive_mutex> lock(mutex_);
        dropped = propagateInformation<MeasurementReceived>(info_received);
    }
    if (!dropped) {
        // Emit the event if it is not dropped
        Orchestrator::get().emitLater(std::move(info_received), info_received.time_received);
    }
}

void InformationFlowModel::handleControlSent(const ControlSent& info) {
    if (info.flags.real_time_critical) {
        return;  // Already propagated by handleRealTimeCriticalControl
    }
    // Copy info in a ControlReceived event (with time_received=current_time)
    auto info_received = ControlReceived(info, Orchestrator::get().getCurrentTime());
    // Apply delay, drop and corruption functions on the created ControlReceived event (possibly modifying info.time_received and info.value)
    bool dropped;
    {
        std::lock_guard<std::recursive_mutex> lock(mutex_);
        dropped = propagateInformation<ControlReceived>(info_received);
    }
    if (!dropped) {
        // Emit the event if it is not dropped
        Orchestrator::get().emitLater(std::move(info_received), info_received.time_received);
    }
}

void InformationFlowModel::handleAcknowledgementSent(const AcknowledgementSent& info) {
    if (info.flags.real_time_critical) {
        return;  // Already propagated by handleRealTimeCriticalControl
    }
    auto info_received = AcknowledgementReceived(info, Orchestrator::get().getCurrentTime());
    bool dropped;
    {
        std::lock_guard<std::recursive_mutex> lock(mutex_);
        dropped = propagateInformation<AcknowledgementReceived>(info_received);
    }
    if (!dropped) {
        Orchestrator::get().emitLater(std::move(info_received), info_received.time_received);
    }
}

void InformationFlowModel::onControlReceived(const ControlReceived& info) {
    if (info.flags.real_time_critical) {
        return;  // Acknowledgement already computed and returned to the caller by handleRealTimeCriticalControl
    }
    auto acknowledgement = makeAcknowledgement(info);
    if (acknowledgement.has_value()) {
        Orchestrator::get().emit(*acknowledgement);
    }
}

std::optional<std::string> InformationFlowModel::getSourceName(const Information& info) const {
    if (info.path.empty()) {
        return std::nullopt;
    }
    return network_graph_->getNode(info.path.front()).getName();
}

std::optional<AcknowledgementSent> InformationFlowModel::makeAcknowledgement(const ControlReceived& control) const {
    auto source = getSourceName(control);
    if (!source.has_value()) {
        return std::nullopt;  // No source to acknowledge to
    }
    std::optional<tase2::Tase2Extension> tase2_data = control.tase2_data;
    if (tase2_data.has_value()) {
        tase2_data->cause = tase2::CAUSE_ACTIVATION_CONFIRMATION;
    }
    return AcknowledgementSent(control.id, control.value, control.time_received, *source, getReturnPath(control),
                               control.topic, std::move(tase2_data), control.control_uid, control.flags, control.time_sent);
}

std::optional<AcknowledgementReceived> InformationFlowModel::handleRealTimeCriticalControl(const ControlSent& control) {
    std::optional<ControlReceived> control_received;
    std::optional<AcknowledgementSent> acknowledgement_sent;
    std::optional<AcknowledgementReceived> acknowledgement_received;
    {
        std::lock_guard<std::recursive_mutex> lock(mutex_);
        control_received.emplace(control, control.time_sent);
        if (propagateInformation<ControlReceived>(*control_received)) {
            control_received.reset();  // Dropped
        } else {
            acknowledgement_sent = makeAcknowledgement(*control_received);
            if (acknowledgement_sent.has_value()) {
                acknowledgement_received.emplace(*acknowledgement_sent, acknowledgement_sent->time_sent);
                if (propagateInformation<AcknowledgementReceived>(*acknowledgement_received)) {
                    acknowledgement_received.reset();  // Dropped
                }
            }
        }
    }

    // The control follows the usual path through the event queue (thread-safe scheduling), received by all modules.
    // The acknowledgement is scheduled for logging only (other modules skip real-time critical acknowledgements).
    Orchestrator::get().emitLater(ControlSent(control), control.time_sent);
    if (control_received.has_value()) {
        double time_received = control_received->time_received;
        Orchestrator::get().emitLater(std::move(*control_received), time_received);
    }
    if (acknowledgement_sent.has_value()) {
        double time_sent = acknowledgement_sent->time_sent;
        Orchestrator::get().emitLater(std::move(*acknowledgement_sent), time_sent);
    }
    if (acknowledgement_received.has_value()) {
        Orchestrator::get().emitLater(AcknowledgementReceived(*acknowledgement_received), acknowledgement_received->time_received);
    }
    return acknowledgement_received;
}

void InformationFlowModel::handleDumpStateEvent(const DumpStateEvent& event) {
    std::ostringstream bin(std::ios::binary);
    ser20::BinaryOutputArchive archive(bin);
    archive(*this);
    logger_.saveDump("InformationFlowModel", event.time, bin.str());
}

std::vector<graaf::vertex_id_t> InformationFlowModel::getPath(const std::string& source, const std::string& destination) const {
    return network_graph_->getPath(source, destination);
}

template<typename T>
bool InformationFlowModel::propagateInformation(T& info) {
    graaf::vertex_id_t sender;
    graaf::vertex_id_t receiver;
    bool dropped = false;

    if (info.path.size() < 1) {
        throw std::runtime_error("Information routing should contain at least 1 elements: " + std::string(info));
    }
    // Case: routing with a single element
    if (info.path.size() == 1) {
        receiver = info.path.front();
        dropped = network_graph_->getNode(receiver).apply(info);
        return dropped;
    }

    // Case: routing with multiple elements
    auto it = info.path.begin();
    sender = *it;
    it++;
    do {
        receiver = *it;

        if (sender == receiver) {
            it++;
            continue;
        }

        dropped = network_graph_->getNode(sender).apply(info);
        if (dropped)
            return true;

        dropped = network_graph_->getLink(sender, receiver).apply(info);
        if (dropped)
            return true;

        sender = *it;
        it++;
    } while (it != info.path.end());

    dropped = network_graph_->getNode(receiver).apply(info);
    return dropped;
}
