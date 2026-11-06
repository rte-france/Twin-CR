/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef CYCOSIM_SOCKET_H
#define CYCOSIM_SOCKET_H

#include <nlohmann/json.hpp>
#include <optional>
#include <zmq.hpp>
#include <string>

class CycosimSocket {
public:
    explicit CycosimSocket(const std::string& zmq_address);

    /**
     * Receive a reply from Cycosim, return std::nullopt if interupted by SignalHandler::gotExistSignal())
     */
    std::optional<nlohmann::json> receive();

    /**
     * Receive with time out. Returns empty json on timeout
     * Should only be used when stopping the simulation to avoid breaking the strict synchronisation
     */
    std::optional<nlohmann::json> attempt_receive(long timeout_ms);

    void send(const nlohmann::json& msg);

private:
    zmq::context_t zmq_context_;
    zmq::socket_t  zmq_socket_;
    zmq::pollitem_t zmq_pollitem_;
};

#endif  // CYCOSIM_SOCKET_H
