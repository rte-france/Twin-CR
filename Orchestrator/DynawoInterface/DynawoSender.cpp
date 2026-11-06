/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DynawoSender.h"
#include "Information.h"
#include "Orchestrator.h"
#include "SignalHandler.h"

#include <spdlog/spdlog.h>

#include <sstream>

DynawoSender::DynawoSender(int port):
socket_(context_, zmq::socket_type::req) {
    std::stringstream address;
    address << "tcp://localhost:" << port;
    socket_.connect(address.str());
}

void DynawoSender::sendAction(const std::string& command) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (command == "step") {
        spdlog::warn("Warning, step command is reserved for goToNextTimeStep(), command disregarded");
    } else if (command == "stop") {
        spdlog::warn("Warning, 'stop' command is reserved for stopDynawo(), command disregarded");
    } else {
        action_queue_.push_back(command);
    }
}

bool DynawoSender::waitForReply() {
    zmq::pollitem_t items[] = {{static_cast<void*>(socket_), 0, ZMQ_POLLIN, 0}};
    while (!zmq::poll(items, 1, std::chrono::milliseconds(1000)) && !SignalHandler::gotExitSignal()) {
        spdlog::warn("DynawoSender: waiting acknowledgement");
    }

    if (SignalHandler::gotExitSignal()) {
        return false;
    }

    zmq::message_t zmq_reply;
    auto res = socket_.recv(zmq_reply);
    if (!res) {
        return false;
    }

    const std::string reply = zmq_reply.to_string();
    spdlog::trace("Sender: Dynawo replied with \"{}\"", reply);
    return reply != "stop signal" && reply != "simulation ended";
}

std::string DynawoSender::goToNextTimeStep() {
    std::lock_guard<std::mutex> lock(mutex_);  // Non thread-safe (need to wait for reply before allowing other threads to send)

    if (!action_queue_.empty()) {
        const std::string ACTION_TAG = "action";
        send("action", zmq::send_flags::sndmore);
        while (!action_queue_.empty()) {
            const std::string command = action_queue_.front();
            action_queue_.pop_front();
            const bool lastCommand = action_queue_.empty();

            send(command, lastCommand ? zmq::send_flags::none : zmq::send_flags::sndmore);
            spdlog::debug("Sending action: \"{}\"", command);
        }

        if (!waitForReply()) {
            return "stop";
        }
    }

    send("step", zmq::send_flags::none);
    spdlog::debug("Sending step trigger");

    if (!waitForReply()) {
        return "stop";
    }

    return "continue";
}

void DynawoSender::stopDynawo() {
    std::lock_guard<std::mutex> lock(mutex_);
    action_queue_.clear();

    spdlog::debug("Stopping Dynawo");

    // Do not wait for a reply from Dynawo as it might not send it if it is interrupted
    send("stop", zmq::send_flags::none);
}

void DynawoSender::send(const std::string& command, zmq::send_flags flag) {
    // Emit event for logging purposes only
    Orchestrator::get().emit(RawDynawoCommand(command, static_cast<int>(flag), event_count_++, Orchestrator::get().getCurrentTime()));

    socket_.send(zmq::buffer(command), flag);
}
