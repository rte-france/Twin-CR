/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef PROCESS_LAUNCHER_H
#define PROCESS_LAUNCHER_H

extern "C" {
#include "subprocess.h"
}

#include <atomic>
#include <string>


/**
 * Class responsible launching a given subprocess (e.g. Dynawo).
 * Due to the risks in creating a subprocess/fork from a multithreaded-process, this class should be instantiated at the very start
 * of the program (before any threads are created). The start(cmd) function can then be called at any time (even after threads are created)
 * to actually launch the subprocess.
 * See https://stackoverflow.com/questions/53601200/calling-fork-on-a-multithreaded-process and in particular
 * https://stackoverflow.com/questions/53601200/calling-fork-on-a-multithreaded-process#comment94067988_53601200
 * for more info.
 */
class ProcessLauncher {
    public:
        ProcessLauncher();
        ~ProcessLauncher();

        // Disallow copy
        ProcessLauncher(const ProcessLauncher&) = delete;
        ProcessLauncher& operator=(const ProcessLauncher&) = delete;

        void start(const std::string& cmd);

        void kill();

        int read_output(char *const buffer, unsigned int size);

    private:
        subprocess_s subprocess_;
        std::atomic<bool> cmd_running_;
        std::string cmd_;
};

#endif // PROCESS_LAUNCHER_H
