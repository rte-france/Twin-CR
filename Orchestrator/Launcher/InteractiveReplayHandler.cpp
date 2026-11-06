/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "InteractiveReplayHandler.h"
#include "Orchestrator.h"

#include <csignal>
#include <deque>


std::atomic<bool> interrupted = false;

inline void replaySignalHandler(int signal) {
    if (signal == SIGINT) {
        interrupted = true;
    }
    std::cout << "Interrupting command..." << std::endl;
}

/**
 * Split a string by whitespace (multiple consecutive whitespaces are treated as one)
 */
std::deque<std::string> split(const std::string& str) {
    std::istringstream iss(str);
    std::string part;
    std::deque<std::string> parts;

    while (iss >> part) {
        parts.push_back(part);
    }
    return parts;
}

InteractiveReplayHandler::InteractiveReplayHandler(Replay& replay, double end_time) :
replay_(replay),
end_time_(end_time) {
    //
}

void InteractiveReplayHandler::start_interactive_session() {
    // Interrupt current command on ctrl C
    signal(SIGINT, replaySignalHandler);

    // Start simulation
    double current_time = 0;
    std::cout << "Command line interface of the replay functionality" << std::endl;
    printAvailableCommands();

    std::string command;
    std::deque<std::string> command_parts;
    std::deque<std::string> args;
    while (true) {
        std::cout << "> ";
        std::getline(std::cin, command);
        command_parts = split(command);

        if (command_parts.empty()) continue;

        // Reset interrupted flag for each new command
        interrupted = false;

        command = command_parts[0];
        command_parts.pop_front();
        args = command_parts;

        if (command == "exit") {
            break;
        }

        if (command == "help") {
            printAvailableCommands();

        } else if (command == "goToTime") {
            if (args.empty()) {
                std::cout << "Please specify to which time to go to" << std::endl;
                printAvailableCommands();
                continue;
            }
            double next_time = std::stod(args[0]);
            double speedup = (args.size() > 1) ? std::stod(args[1]) : 1;
            goToTime(current_time, next_time, speedup);

        } else if (command == "jumpToTime") {
            if (args.empty()) {
                std::cout << "Please specify to which time to jump to" << std::endl;
                printAvailableCommands();
                continue;
            }
            double next_time = std::stod(args[0]);
            jumpToTime(current_time, next_time);

        } else if (command == "setTopicFilter") {
            std::string filter = (args.size() > 0) ? args[0] : "";
            setTopicFilter(filter);

        } else {
            std::cout << "Unknown command" << std::endl;
            printAvailableCommands();
        }

        if (current_time >= end_time_) {
            std::cout << "Reached end of replay, closing..." << std::endl;
            break;
        }
    }
}

void InteractiveReplayHandler::printAvailableCommands() {
    std::cout << "Available commands are:" << std::endl;
    std::cout << "\thelp" << std::endl;
    std::cout << "\texit" << std::endl;
    std::cout << "\tgoToTime time speedup(=1)" << std::endl;
    std::cout << "\tjumpToTime time" << std::endl;
    std::cout << "\tsetTopicFilter filter(=\"\")" << std::endl;
}

void InteractiveReplayHandler::goToTime(double& current_time, double end_time, double speedup) {
    replay_.setTargetTime(end_time);
    Orchestrator::get().setSpeedUp(speedup);
    Orchestrator::get().resetRealTimeClock(current_time);
    double next_time = current_time + 1;
    while (!interrupted && next_time < end_time) {  // Check every second that ctrl C has not been caught
        Orchestrator::get().run(next_time);
        current_time = next_time;
        next_time += 1;
    }

    if (!interrupted) {
        Orchestrator::get().run(end_time);
        current_time = end_time;
    }
}

void InteractiveReplayHandler::jumpToTime(double& current_time, double end_time) {
    replay_.jumpToTime(end_time);
    Orchestrator::get().setSpeedUp(999);
    Orchestrator::get().resetRealTimeClock(current_time);
    Orchestrator::get().run(end_time);
    current_time = end_time;
}

void InteractiveReplayHandler::setTopicFilter(const std::string& filter) {
    replay_.setTopicFilter(filter);
}
