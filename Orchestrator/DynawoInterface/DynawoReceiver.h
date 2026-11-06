/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DYNAWO_RECEIVER_H
#define DYNAWO_RECEIVER_H

#include <string>
#include <vector>
#include <zmq.hpp>

class DynawoReceiver {
    public:
        DynawoReceiver(int port, const std::string& topic);

        std::string receive_string();

        std::vector<double> receive_bytes();
    private:
        zmq::context_t context_{1};
        zmq::socket_t socket_;
        std::string topic_;
};

#endif // DYNAWO_RECEIVER_H
