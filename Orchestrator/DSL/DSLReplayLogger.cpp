/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLReplayLogger.h"

DSLReplayLogger::DSLReplayLogger(const std::filesystem::path& path) :
path_(path),
stream_(path, std::ios::out | std::ios::app) {}

DSLReplayLogger::~DSLReplayLogger() {
    close();
}

void DSLReplayLogger::logLine(const std::string& dsl_line) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!stream_.is_open()) return;
    stream_ << dsl_line << "\n";
    stream_.flush();
}

void DSLReplayLogger::close() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (stream_.is_open()) stream_.close();
}
