/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "CycosimSocket.h"
#include "SignalHandler.h"
#include <optional>
#include <spdlog/spdlog.h>
#include <stdexcept>

CycosimSocket::CycosimSocket(const std::string& zmq_address) :
zmq_context_(1),
zmq_socket_(zmq_context_, zmq::socket_type::req) {
    try {
        zmq_socket_.connect(zmq_address);
        zmq_pollitem_ = {static_cast<void*>(zmq_socket_), 0, ZMQ_POLLIN, 0};
    } catch (std::exception& e) {
        throw std::runtime_error("CycosimSocket: Failed to connect to " + zmq_address);
    }
}

std::optional<nlohmann::json> CycosimSocket::receive() {
    while (!zmq::poll(&zmq_pollitem_, 1, std::chrono::milliseconds(1000)) && !SignalHandler::gotExitSignal()) {
        spdlog::warn("CycosimSocket: Waiting for reply");
    }
    if (SignalHandler::gotExitSignal()) {
        return std::nullopt;
    }
    zmq::message_t message;
    auto res = zmq_socket_.recv(message);
    if (!res) {
        throw std::runtime_error("CycosimSocket: Error during ZMQ message reception");
    }
    std::string msg_str = message.to_string();
    try {
        return nlohmann::json::parse(msg_str);
    } catch (const nlohmann::json::parse_error& e) {
        throw std::runtime_error("CycosimSocket: Failed to parse message: " + msg_str + " error: " + e.what());
    }
}

std::optional<nlohmann::json> CycosimSocket::attempt_receive(long timeout_ms) {
    if (!zmq::poll(&zmq_pollitem_, 1, std::chrono::milliseconds(timeout_ms))) {
        return std::nullopt;
    }
    return receive();
}

void CycosimSocket::send(const nlohmann::json& msg) {
    std::string data = msg.dump();
    zmq::message_t message(data.size());
    memcpy(message.data(), data.data(), data.size());
    zmq_socket_.send(message, zmq::send_flags::none);
    spdlog::debug("CycosimSocket: Sending: \"{}\"", msg.dump());
}
