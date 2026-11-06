/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef SIGNAL_HANDLER_H
#define SIGNAL_HANDLER_H

#include <atomic>

/**
 * @brief Signal handler class
 *
 * Signal handler object intercepts signal (e.g. ctrl+C) from the outside
 */
class SignalHandler {
    public:
        static bool gotExitSignal();

        static void create();

        static void interrupt();

    private:
        static void setExitSignal(bool exitSignal);

        static void exitSignalHandler(int signal);

    private:
        static std::atomic<bool> gotExitSignal_;
        static std::atomic<int> lastSignal_;
};

#endif  // SIGNAL_HANDLER_H
