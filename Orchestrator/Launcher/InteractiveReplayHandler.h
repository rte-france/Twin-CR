/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


#ifndef INTERACTIVE_REPLAY_HANDLER_H
#define INTERACTIVE_REPLAY_HANDLER_H

#include "Replay.h"

#include <string>

/**
 * Command-line interactive prompt to control the replay of a simulation
 */
class InteractiveReplayHandler {
    public:
        InteractiveReplayHandler(Replay& replay, double end_time);

        void start_interactive_session();
        void terminate();
        void printAvailableCommands();
        void goToTime(double& current_time, double end_time, double speedup = 1);
        void jumpToTime(double& current_time, double end_time);

        /**
        * Set a filter to only emit events that exactly match the topic filter.
        * "" (empty) means no filter
        * Events without a defined topic (e.g. TimeUpdate) are always emitted
        */
        void setTopicFilter(const std::string& filter);

    private:
        Replay& replay_;
        double end_time_;

};

#endif // INTERACTIVE_REPLAY_HANDLER_H
