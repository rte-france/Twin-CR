/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DYNAWO_SENDER_H
#define DYNAWO_SENDER_H

#include <deque>
#include <string>
#include <mutex>
#include <zmq.hpp>

class DynawoSender {
    public:
        DynawoSender(int port);

        /**
         * Send a command to Dynawo.
         * The command is actually saved in a queue, and will be sent to Dynawo on the next goToNextTimeStep() call
         */
        void sendAction(const std::string& command);

        /**
         * Push queued commands, then send a signal to Dynawo to proceed to the next time step (via empty command)
         * Returns "continue" if Dynawo correctly handled the command and proceeds to the next time step
         * Returns "stop" if Dynawo was interrupted
         */
        std::string goToNextTimeStep();

        void stopDynawo();

    private:
        void send(const std::string& command, zmq::send_flags flag);

        [[nodiscard]] bool waitForReply();

        zmq::context_t context_{1};
        zmq::socket_t socket_;
        std::deque<std::string> action_queue_;
        std::mutex mutex_;
        uint64_t event_count_ = 0;
};

#endif // DYNAWO_SENDER_H