/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


#ifndef LOGGER_DATABASE_H
#define LOGGER_DATABASE_H

#include "Information.h"
#include "../utils/ClickHouseLoggerInterface.h"
#include "ThreadPool.h"

#include <curl/curl.h>

#include <mutex>
#include <unordered_map>
#include <unordered_set>

/**
 * Class that monitors all information going through the simulation and logs them to a database
 */
class ClickHouseLogger : public ClickHouseLoggerInterface {
    public:
        ClickHouseLogger(std::filesystem::path config_path, const std::string& base_db_name = "", double start_time = 0, bool save_input_files = true);

        ~ClickHouseLogger();

        void cleanup();

        /**
         * Serialize the information and put it in a buffer. Buffers are pushed to the ClickHouse DB on each TimeUpdate
         * Buffering is necessary for performance (cannot make >100k db requests per second)
         */
        template<typename T>
        void logInformation(const T& info) {
            if constexpr (std::is_same_v<T, TimeUpdate>) {
                // Push buffers each time a TimeUpdate is received
                pushBuffers();
                pushTimeUpdate(info);
            } else if constexpr (std::is_same_v<T, ActualMeasurement>) {
                info.serialize(information_buffers_[info.getType()]);
                information_buffers_[info.getType()].write(actual_measurements_count_++);
            } else {
                info.serialize(information_buffers_[info.getType()]);
            }
        }

        void logGameMasterCommand(double time, const std::string& command_source, const std::string& command);

        void logSCADACommand(double time, const std::string& command_source, const std::string& command);

        void saveDump(const std::string& dump_name, double time, const std::string& bin) override;

        std::string loadDump(const std::string& dump_name, double time) override;

        void logInputFile(const std::filesystem::path& path);
        void logOutputFile(const std::filesystem::path& path) override;

        /**
         * Fetch the input files from the clickhouse database in table simulation_id.input_files,
         * then write the files to a temporary folder.
         */
        static void fetch_input_files_from_simulation_id(const std::string& simulation_id);

    private:
        void logFile(const std::filesystem::path& path, const std::string& table_name);
        void createTables();
        void createTableViews(const std::string& base_db_name, double start_time);
        std::string execQuery(const std::string& query);
        void pushBuffer(const ClickHouseBinaryBuffer& buffer, const std::string& table_name);
        void pushBuffers();
        void pushTimeUpdate(const TimeUpdate& time_update);
        void saveInputFiles();
        static std::vector<char> getBuffer(CURL* curl, const std::string& query, int max_retries=3, std::chrono::milliseconds backoff=std::chrono::milliseconds(100));

        std::string getFullTableName(const std::string& table_name) const;

        std::string endpoint_;
        std::string credentials_;
        std::string db_name_;
        CURL* curl_;
        std::mutex curl_mutex_;
        std::filesystem::path config_path_;
        std::unordered_map<int, ClickHouseBinaryBuffer> information_buffers_;
        std::unordered_map<std::string, ClickHouseBinaryBuffer> command_buffers_;
        std::mutex mutex_;
        std::unordered_map<std::string, std::unordered_set<std::filesystem::path>> saved_paths_;
        ThreadPool pool_{std::thread::hardware_concurrency()};
        std::string base_db_name_;
        uint64_t actual_measurements_count_ = 1;  // 0 is reserved for measurements from previous dumps
};

#endif // LOGGER_DATABASE_H
