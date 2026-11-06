/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef CLICKHOUSE_LOGGER_INTERFACE_H
#define CLICKHOUSE_LOGGER_INTERFACE_H

#include <filesystem>
#include <string>

/**
 * Interface of the ClickHouseLogger. Currently implemented by the ClickHouseLogger itself and by a mock (testing/TmpDirClickHouseLogger.h)
 */
class ClickHouseLoggerInterface {
    public:
        virtual ~ClickHouseLoggerInterface() = default;
        virtual void saveDump(const std::string& dump_name, double time, const std::string& bin) = 0;
        virtual std::string loadDump(const std::string& dump_name, double time) = 0;
        virtual void logOutputFile(const std::filesystem::path& path) = 0;
};

#endif // CLICKHOUSE_LOGGER_INTERFACE_H
