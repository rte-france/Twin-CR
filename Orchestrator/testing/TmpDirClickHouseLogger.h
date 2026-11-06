/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef TMP_DIR_CLICKHOUSE_LOGGER_H
#define TMP_DIR_CLICKHOUSE_LOGGER_H

#include "../utils/ClickHouseLoggerInterface.h"

#include <fstream>
#include <iterator>
#include <random>
#include <stdexcept>
#include <string>
#include <system_error>

/**
 * A simple mock of ClickHouseLogger backed by a tmp directory instead of ClickHouse.
 */
class TmpDirClickHouseLogger : public ClickHouseLoggerInterface {
    public:
        explicit TmpDirClickHouseLogger(const std::string& label = "orchestrator_test") {
            // Deliberately not mkdtemp, which needs <unistd.h> and does not exist on Windows. create_directory
            // reports whether it was the one that created the directory, so retrying on a clash is enough to end
            // up with one this instance alone owns.
            std::mt19937 generator{std::random_device{}()};
            std::uniform_int_distribution<unsigned long> suffix(0, 0xFFFFFFUL);
            for (int attempt = 0; attempt < 100; attempt++) {
                auto candidate = std::filesystem::temp_directory_path() / (label + "_" + std::to_string(suffix(generator)));
                std::error_code failed;
                if (std::filesystem::create_directory(candidate, failed) && !failed) {
                    directory_ = candidate;
                    return;
                }
            }
            throw std::runtime_error("Cannot create a temporary directory for " + label);
        }

        ~TmpDirClickHouseLogger() override {
            if (keep_) return;
            // Delete the tmp dir
            std::error_code ignored;  // a destructor must not throw, and a leftover temp directory is not fatal
            std::filesystem::remove_all(directory_, ignored);
        }

        TmpDirClickHouseLogger(const TmpDirClickHouseLogger&) = delete;
        TmpDirClickHouseLogger& operator=(const TmpDirClickHouseLogger&) = delete;

        /**
         * Leaves the directory in place instead of removing it, so a failing test's dumps and archived files can
         * still be looked at afterwards.
         */
        void keep() { keep_ = true; }

        void saveDump(const std::string& dump_name, double time, const std::string& bin) override {
            std::ofstream out(pathFor(dump_name, time), std::ios::binary);
            out.write(bin.data(), static_cast<std::streamsize>(bin.size()));
        }

        std::string loadDump(const std::string& dump_name, double time) override {
            std::ifstream in(pathFor(dump_name, time), std::ios::binary);
            if (!in.is_open()) {
                throw std::runtime_error("No dump stored for " + dump_name + " at t=" + std::to_string(time));
            }
            return std::string((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        }

        void logOutputFile(const std::filesystem::path& path) override {
            if (!std::filesystem::exists(path)) return;
            std::filesystem::copy_file(path, directory_ / path.filename(), std::filesystem::copy_options::overwrite_existing);
        }

        const std::filesystem::path& directory() const { return directory_; }

    private:
        std::filesystem::path pathFor(const std::string& dump_name, double time) const {
            return directory_ / (dump_name + "_" + std::to_string(time) + ".dump");
        }

        std::filesystem::path directory_;
        bool keep_ = false;
};

#endif // TMP_DIR_CLICKHOUSE_LOGGER_H
