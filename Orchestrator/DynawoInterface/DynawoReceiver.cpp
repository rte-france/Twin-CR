/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DynawoReceiver.h"
#include "SignalHandler.h"

#include <spdlog/spdlog.h>

#include <sstream>
#include <stdexcept>

DynawoReceiver::DynawoReceiver(int port, const std::string& topic):
socket_(context_, zmq::socket_type::sub),
topic_(topic) {
    std::stringstream address;
    address << "tcp://localhost:" << port;
    socket_.set(zmq::sockopt::reconnect_ivl, 1);
    socket_.connect(address.str());
    socket_.set(zmq::sockopt::subscribe, topic);
}

std::string DynawoReceiver::receive_string() {
    // Polling
    zmq::pollitem_t items[] = {{static_cast<void*>(socket_), 0, ZMQ_POLLIN, 0}};
    while (!zmq::poll(items, 1, std::chrono::milliseconds(1000)) && !SignalHandler::gotExitSignal()) {
        spdlog::warn("DynawoReceiver: Trying to read on topic {}", topic_);
    }
    if (SignalHandler::gotExitSignal()) {
        return "stop";
    }

    zmq::message_t topic_msg;
    zmq::message_t content_msg;
    auto res_topic = socket_.recv(topic_msg);
    if (!res_topic || !socket_.get(zmq::sockopt::rcvmore)) {
        throw std::runtime_error("Error: invalid topic content for ZMQ string data message");;
    }
    auto res_content = socket_.recv(content_msg);
    if (!res_content) {
        throw std::runtime_error("Error: invalid content for ZMQ string data message");;
    }

    return content_msg.to_string();
}

std::vector<double> DynawoReceiver::receive_bytes() {
    // Polling
    zmq::pollitem_t items[] = {{static_cast<void*>(socket_), 0, ZMQ_POLLIN, 0}};
    while (!zmq::poll(items, 1, std::chrono::milliseconds(1000)) && !SignalHandler::gotExitSignal()) {
        spdlog::warn("DynawoReceiver: Trying to read on topic {}", topic_);
    }
    if (SignalHandler::gotExitSignal()) {
        return {};
    }

    zmq::message_t topic_msg;
    zmq::message_t data_msg;
    auto res_topic = socket_.recv(topic_msg);
    if (!res_topic || !socket_.get(zmq::sockopt::rcvmore)) {
        throw std::runtime_error("Error: invalid topic content for ZMQ bytes data message");;
    }
    auto res_data = socket_.recv(data_msg);
    if (!res_data) {
        throw std::runtime_error("Error: invalid content for ZMQ bytes data message");;
    }

    const double* double_data = static_cast<const double*>(data_msg.data());
    return std::vector<double>(double_data, double_data + (data_msg.size() / sizeof(double)));
}
