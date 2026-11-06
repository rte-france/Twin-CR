/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_REPLAY_LOGGER_H
#define DSL_REPLAY_LOGGER_H

#include <filesystem>
#include <fstream>
#include <mutex>

/**
 * Append-only, human-/DSL-readable log of everything the DSL engine actually did, timed in absolute simulation time so the file is itself a valid,
 * directly re-runnable PowerEventDSL script. Uploaded via ClickHouseLogger::logOutputFile on shutdown.
 * Note that due to limitations of the DSL grammar, the generated replay script is not fully equivalent to the actual simulation,
 * e.g., it is not possible to schedule the creation of a when/after clause, so all when/after clauses are written as being created at the start of the
 * simulation in this replay file. (This is fully independent of the ser20 dump/load functionality of the DSLEngine that is exact.)
 */
class DSLReplayLogger {
    public:
        explicit DSLReplayLogger(const std::filesystem::path& path);
        ~DSLReplayLogger();

        void logLine(const std::string& dsl_line);
        void close();
        const std::filesystem::path& path() const { return path_; }

    private:
        std::filesystem::path path_;
        std::ofstream stream_;
        std::mutex mutex_;
};

#endif // DSL_REPLAY_LOGGER_H
