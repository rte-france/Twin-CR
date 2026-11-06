/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "SignalHandler.h"
#include "spdlog/spdlog.h"
#include <csignal>
#include <cerrno>
#include <cstdlib>

#if !defined(_WIN32)
#include <execinfo.h>
#include <unistd.h>
#endif


std::atomic<bool> SignalHandler::gotExitSignal_ = false;
std::atomic<int> SignalHandler::lastSignal_ = 0;

bool SignalHandler::gotExitSignal() {
    // Logging is deferred to here (normal execution context) rather than done in
    // exitSignalHandler() itself, since spdlog is not async-signal-safe.
    const int sig = lastSignal_.exchange(0);
    if (sig != 0) {
        switch (sig) {
            #ifdef SIGTERM
            case SIGTERM:
                spdlog::error("Received SIGTERM signal");
                break;
            #endif
            #ifdef SIGINT
            case SIGINT:
                spdlog::error("Received SIGINT signal");
                break;
            #endif
            #ifdef SIGQUIT
            case SIGQUIT:
                spdlog::error("Received SIGQUIT signal");
                break;
            #endif
            default:
                break;
        }
    }
    return gotExitSignal_;
}

static void sigsegvHandler(int /*sig*/) {
    // Async-signal-safe: use write() and _exit()
    const char msg[] = "\n*** SIGSEGV caught in orchestrator_exec ***\n";
    volatile ssize_t ignored = write(STDERR_FILENO, msg, sizeof(msg) - 1);
    (void) ignored;
#if !defined(_WIN32)
    void* array[64];
    int size = backtrace(array, 64);
    backtrace_symbols_fd(array, size, STDERR_FILENO);
#endif
    // Restore default handler and re-raise to get core dump
    signal(SIGSEGV, SIG_DFL);
    raise(SIGSEGV);
}

void SignalHandler::create() {
    #ifdef SIGTERM
    signal(SIGTERM, SignalHandler::exitSignalHandler);
    #endif
    #ifdef SIGINT
    signal(SIGINT, SignalHandler::exitSignalHandler);
    #endif
    #ifdef SIGQUIT
    signal(SIGQUIT, SignalHandler::exitSignalHandler);
    #endif
    // Add SIGSEGV handler for diagnostics
    signal(SIGSEGV, sigsegvHandler);
}

void SignalHandler::interrupt() {
    spdlog::error("Simulation interrupted");
    gotExitSignal_ = true;
}

void SignalHandler::setExitSignal(const bool exitSignal) {
    gotExitSignal_ = exitSignal;
}

void SignalHandler::exitSignalHandler(const int signal) {
    // This function must be async-signal safe
    lastSignal_ = signal;
    setExitSignal(true);
}
