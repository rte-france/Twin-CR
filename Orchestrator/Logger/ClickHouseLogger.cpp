/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "ClickHouseLogger.h"
#include "Credentials.h"
#include "Information.h"
#include "Orchestrator.h"

#include <spdlog/spdlog.h>

#include <future>
#include <sstream>
#include <string>
#include <unordered_map>


ClickHouseLogger::ClickHouseLogger(std::filesystem::path config_path, const std::string& base_db_name, double start_time, bool save_input_files) :
config_path_(config_path), base_db_name_(base_db_name) {

    endpoint_ = Credentials::get().getClickhouseURL();
    credentials_ = Credentials::get().getClickhouseCredentials();

    curl_global_init(CURL_GLOBAL_ALL);
    curl_ = curl_easy_init();
    if (!curl_) throw std::runtime_error("CURL init failed");

    db_name_ = Orchestrator::get().getSimulationName();
    execQuery("CREATE DATABASE IF NOT EXISTS " + db_name_);

    createTables();
    createTableViews(base_db_name, start_time);
    if (save_input_files)
        saveInputFiles();

    bool log_all_events = Orchestrator::get().getConfig()["master"]["log_all_events"].value_or(true);
    if (log_all_events) {
        Orchestrator::get().subscribeTo<MeasurementSent, &ClickHouseLogger::logInformation<MeasurementSent>>(this);
        Orchestrator::get().subscribeTo<MeasurementReceived, &ClickHouseLogger::logInformation<MeasurementReceived>>(this);
        Orchestrator::get().subscribeTo<ControlSent, &ClickHouseLogger::logInformation<ControlSent>>(this);
        Orchestrator::get().subscribeTo<ControlReceived, &ClickHouseLogger::logInformation<ControlReceived>>(this);
        Orchestrator::get().subscribeTo<ActualMeasurement, &ClickHouseLogger::logInformation<ActualMeasurement>>(this);
        Orchestrator::get().subscribeTo<ActualControl, &ClickHouseLogger::logInformation<ActualControl>>(this);
    }
    Orchestrator::get().subscribeTo<TimeUpdate, &ClickHouseLogger::logInformation<TimeUpdate>>(this);
    Orchestrator::get().subscribeTo<DynawoTimelineEvent, &ClickHouseLogger::logInformation<DynawoTimelineEvent>>(this);
    Orchestrator::get().subscribeTo<DynawoConstraintEvent, &ClickHouseLogger::logInformation<DynawoConstraintEvent>>(this);
    Orchestrator::get().subscribeTo<DumpStateEvent, &ClickHouseLogger::logInformation<DumpStateEvent>>(this);
    Orchestrator::get().subscribeTo<RawDynawoCommand, &ClickHouseLogger::logInformation<RawDynawoCommand>>(this);
}

void ClickHouseLogger::cleanup() {
    pushBuffers();
    pool_.waitAll();
}

ClickHouseLogger::~ClickHouseLogger() {
    cleanup();

    if (curl_) curl_easy_cleanup(curl_);
    curl_global_cleanup();
}

std::string ClickHouseLogger::getFullTableName(const std::string& table_name) const {
    return "`" + db_name_ + "`.`" + table_name + "`";
}

// Simple response writer for curl
size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    ((std::string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

std::string ClickHouseLogger::execQuery(const std::string& query) {
    std::lock_guard<std::mutex> lock(curl_mutex_);  // Only one thread can access a given CURL instance at a time
    spdlog::trace("Clickhouse query: {}", query);

    std::string response;
    curl_easy_setopt(curl_, CURLOPT_URL, endpoint_.c_str());
    curl_easy_setopt(curl_, CURLOPT_POST, 1L);
    curl_easy_setopt(curl_, CURLOPT_POSTFIELDS, query.c_str());

    curl_easy_setopt(curl_, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl_, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl_, CURLOPT_FAILONERROR, 1);
    if (!credentials_.empty())
        curl_easy_setopt(curl_, CURLOPT_USERPWD, credentials_.c_str());

    CURLcode res = curl_easy_perform(curl_);
    if (res != CURLE_OK) {
        throw std::runtime_error("Query failed: " + std::string(curl_easy_strerror(res)));
    }
    return response;
}

bool isRetryableCurlError(CURLcode code) {
    switch (code) {
        case CURLE_COULDNT_CONNECT:
        case CURLE_OPERATION_TIMEDOUT:
        case CURLE_RECV_ERROR:
        case CURLE_SEND_ERROR:
        case CURLE_GOT_NOTHING:
            return true;
        default:
            return false;
    }
}

std::vector<char> ClickHouseLogger::getBuffer(CURL* curl, const std::string &query, int max_retries, std::chrono::milliseconds backoff) {
    int attempt = 0;
    do {
        attempt++;
        std::vector<char> buffer;
        curl_easy_setopt(curl, CURLOPT_URL, Credentials::get().getClickhouseURL());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, query.c_str());
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 60);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION,
            +[](char* ptr, size_t size, size_t nmemb, void* userdata) -> size_t {
                auto* buf = reinterpret_cast<std::vector<char>*>(userdata);
                buf->insert(buf->end(), ptr, ptr + size * nmemb);
                return size * nmemb;
            });
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &buffer);

        std::string credentials = Credentials::get().getClickhouseCredentials();
        if (!credentials.empty())
            curl_easy_setopt(curl, CURLOPT_USERPWD, credentials.c_str());

        CURLcode res = curl_easy_perform(curl);
        if (res == CURLE_OK)
            return buffer;

        if (!isRetryableCurlError(res) || attempt >= max_retries) {
            throw std::runtime_error(
                std::string("ClickHouse request failed: ") +
                curl_easy_strerror(res)
            );
        }

        std::this_thread::sleep_for(backoff * attempt);
        curl_easy_reset(curl);
    } while (attempt < max_retries);
    throw std::logic_error("Unreachable");  // Delete compiler warning
}

void ClickHouseLogger::createTables() {
    const std::string tase2_columns =
        "tase2_id Nullable(String), "
        "signalisation_type Nullable(Int32), "
        "cause Nullable(Int32), "
        "validity Nullable(Int32), "
        "operatorBlocked Nullable(Bool)";

    std::ostringstream ss;
    // Tables starting with an underscore are "private", a "public" table view will be generated instead (without the leading underscore)
    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_MeasurementSent") << " ("
        << "id String, "
        << "value_type UInt8, "
        << "value Float64, "
        << "time_sent Float64, "
        << "destination String, "
        << "topic String, "
        << tase2_columns
        << ") ENGINE = MergeTree() ORDER BY (topic, time_sent)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_ControlSent") << " ("
        << "id String, "
        << "value_type UInt8, "
        << "value Float64, "
        << "time_sent Float64, "
        << "destination String, "
        << "topic String, "
        << tase2_columns
        << ") ENGINE = MergeTree() ORDER BY (topic, time_sent)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_MeasurementReceived") << " ("
        << "id String, "
        << "value_type UInt8, "
        << "value Float64, "
        << "time_sent Float64, "
        << "destination String, "
        << "topic String, "
        << tase2_columns << ", "
        << "time_received Float64"
        << ") ENGINE = MergeTree() ORDER BY (topic, time_received)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_ControlReceived") << " ("
        << "id String, "
        << "value_type UInt8, "
        << "value Float64, "
        << "time_sent Float64, "
        << "destination String, "
        << "topic String, "
        << tase2_columns << ", "
        << "time_received Float64"
        << ") ENGINE = MergeTree() ORDER BY (topic, time_received)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_ActualMeasurement") << " ("
        << "id String, "
        << "value_type UInt8, "
        << "value Float64, "
        << "time Float64, "
        << "topic String, "
        << "count UInt64"
        << ") ENGINE = MergeTree() ORDER BY (topic, time)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("Latest_ActualMeasurement") << " ("
        << "id String, "
        << "value_type UInt8, "
        << "value Float64, "
        << "time Float64, "
        << "topic String, "
        << "count UInt64"
        << ") ENGINE = ReplacingMergeTree(count) ORDER BY (topic, id)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE MATERIALIZED VIEW IF NOT EXISTS " << getFullTableName("mv_Latest_ActualMeasurement")
        << " TO " << getFullTableName("Latest_ActualMeasurement")
        << " AS SELECT id, value_type, value, time, topic, count FROM " << getFullTableName("_ActualMeasurement");
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_ActualControl") << " ("
        << "id String, "
        << "value_type UInt8, "
        << "value Float64, "
        << "time Float64, "
        << "topic String"
        << ") ENGINE = MergeTree() ORDER BY (topic, time)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_TimeUpdate") << " ("
        << "value Float64"
        << ") ENGINE = MergeTree() ORDER BY (value)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_DynawoTimelineEvent") << " ("
        << "time Float64, "
        << "modelName String, "
        << "message String"
        << ") ENGINE = MergeTree() ORDER BY (time)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_DynawoConstraintEvent") << " ("
        << "description String, "
        << "modelName String, "
        << "time Float64, "
        << "eventType String, "
        << "event_string String"
        << ") ENGINE = MergeTree() ORDER BY (time)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_DumpStateEvent") << " ("
        << "time Float64"
        << ") ENGINE = MergeTree() ORDER BY (time)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_RawDynawoCommand") << " ("
        << "command String, "
        << "zmq_flag Int32, "
        << "event_count UInt64, "
        << "time Float64"
        << ") ENGINE = MergeTree() ORDER BY (event_count)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("InputFiles") << " ("
        << "input_file String, "
        << "content String"
        << ") ENGINE = MergeTree() ORDER BY (input_file)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("OutputFiles") << " ("
        << "output_file String, "
        << "content String"
        << ") ENGINE = MergeTree() ORDER BY (output_file)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_GameMasterCommand") << " ("
        << "time Float64, "
        << "command_source String, "
        << "command String"
        << ") ENGINE = MergeTree() ORDER BY (time)";
    execQuery(ss.str()); ss.str("");

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName("_SCADACommand") << " ("
        << "time Float64, "
        << "command_source String, "
        << "command String"
        << ") ENGINE = MergeTree() ORDER BY (time)";
    execQuery(ss.str()); ss.str("");
}

std::string getTimeKey(const std::string& table_name) {
    if (table_name == "MeasurementReceived" || table_name == "ControlReceived") {
        return "time_received";
    } else if (table_name == "MeasurementSent" || table_name == "ControlSent") {
        return "time_sent";
    } else {
        return "time";
    }
}

void ClickHouseLogger::createTableViews(const std::string& base_db_name, double start_time) {
    std::ostringstream ss;
    // Create "public" view of the "private" tables
    // Those view contain the tables themselves + the view of the simulation they are based on (if base_db_name != "" and start_time > 0)

    ss << "SELECT name FROM system.tables WHERE database = '" << db_name_ << "'";
    std::string tables = execQuery(ss.str()); ss.str("");

    std::istringstream iss(tables);
    std::string table_name;

    while (std::getline(iss, table_name)) {
        if (table_name.empty()) continue;
        if (*table_name.begin() != '_') continue;
        table_name.erase(table_name.begin());  // Erase leading underscore

        if (!base_db_name.empty()) {
            // Simulation starts from a dump, so the table view is the union of the data from the dump (before start_time) and the current db
            ss << "CREATE OR REPLACE VIEW " << getFullTableName(table_name) << " AS "
                    << "SELECT * FROM `" << base_db_name << "`.`" << table_name << "` WHERE " << getTimeKey(table_name) << " < " << start_time << " "
                    << "UNION ALL "
                    << "SELECT * FROM " << getFullTableName("_" + table_name) << ";";
            execQuery(ss.str()); ss.str("");
        } else {
            // Simulation starts from fresh start, table view is simply the table itself (without the leading underscore)
            ss << "CREATE OR REPLACE VIEW " << getFullTableName(table_name) << " AS "
                    << "SELECT * FROM " << getFullTableName("_" + table_name) << ";";
            execQuery(ss.str()); ss.str("");
        }
    }

    if (!base_db_name.empty()) {
        // Initially fill Latest_ActualMeasurement with values from the previous run, setting the count number of all old values to 0
        // so that they are always overwritten when new values arrive
        ss << "INSERT INTO " << getFullTableName("Latest_ActualMeasurement")
            << " SELECT id, value_type, value, time, topic, 0 AS count FROM `" << base_db_name << "`.`Latest_ActualMeasurement`";
        execQuery(ss.str()); ss.str("");
    }
}

void ClickHouseLogger::pushBuffer(const ClickHouseBinaryBuffer& buffer, const std::string& table_name) {
    std::string query = "INSERT INTO " + getFullTableName(table_name) + " FORMAT RowBinary";
    spdlog::trace("Clickhouse query: {}", query);

    CURL* curl = curl_easy_init();  // Use a separate curl instance from the main class to allow for multi-threading
    if (!curl) throw std::runtime_error("CURL init failed");

    // curl_easy_escape returns dynamically allocated memory that must be freed with curl_free
    char* escaped = curl_easy_escape(curl, query.c_str(), static_cast<int>(query.size()));
    if (!escaped) {
        curl_easy_cleanup(curl);
        throw std::runtime_error("curl_easy_escape failed for query: " + query);
    }
    std::string url = endpoint_ + "?query=" + escaped;
    curl_free(escaped);

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, buffer.data());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, buffer.size());
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);          // 30s total timeout
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, 10L);   // 10s connect timeout
    if (!credentials_.empty())
        curl_easy_setopt(curl, CURLOPT_USERPWD, credentials_.c_str());

    CURLcode res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        throw std::runtime_error("Upload failed: " + std::string(curl_easy_strerror(res)));
    }
}

void ClickHouseLogger::pushBuffers() {
    std::vector<std::future<void>> jobs;

    for (auto& [type, buffer] : information_buffers_) {
        if (buffer.size() == 0) continue;

        const std::string& table_name = "_" + SERIALABLE_NAMES.at(type);

        // Each buffer is published by one given thread from a thread pool
        jobs.push_back(pool_.enqueue([this, table_name, buf = std::move(buffer)]() {
            try {
                pushBuffer(buf, table_name);
            } catch (const std::exception& e) {
                spdlog::error("ClickHouseLogger: Failed to push buffer for {}: {}", table_name, e.what());
            }
        }));
        // The buffer has been moved to the publishing thread, so we can continue with a fresh one without waiting for the thread to finish
        buffer = ClickHouseBinaryBuffer{};
    }

    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& [table_name, buffer] : command_buffers_) {
        if (buffer.size() == 0) continue;
        jobs.push_back(pool_.enqueue([this, table_name, buf = std::move(buffer)]() {
            pushBuffer(buf, table_name);
        }));
        buffer = ClickHouseBinaryBuffer{};
    }
}

void ClickHouseLogger::logGameMasterCommand(double time, const std::string& command_source, const std::string& command) {
    const std::string TABLE_NAME = "_GameMasterCommand";
    std::lock_guard<std::mutex> lock(mutex_);
    ClickHouseBinaryBuffer& buffer = command_buffers_[TABLE_NAME];
    ::serialize(buffer, time, command_source, command);
    // Buffer will be pushed on next time update
}

void ClickHouseLogger::logSCADACommand(double time, const std::string& command_source, const std::string& command) {
    const std::string TABLE_NAME = "_SCADACommand";
    std::lock_guard<std::mutex> lock(mutex_);
    ClickHouseBinaryBuffer& buffer = command_buffers_[TABLE_NAME];
    ::serialize(buffer, time, command_source, command);
    // Buffer will be pushed on next time update
}

void ClickHouseLogger::pushTimeUpdate(const TimeUpdate& time_update) {
    ClickHouseBinaryBuffer buffer;
    time_update.serialize(buffer);

    std::string table_name = "_" + SERIALABLE_NAMES.at(int(SerializableInfo::TimeUpdate));
    pushBuffer(buffer, table_name);
}

void ClickHouseLogger::saveInputFiles() {
    std::filesystem::path working_dir = config_path_.parent_path();
    std::unordered_map<std::string, std::string> input_file_paths = {
        {"config", config_path_}
    };

    // Add all input files from the config.toml
    toml::table config = toml::parse_file(config_path_.c_str());
    const auto& input_files = config["input_files"];
    if (!input_files.is_table()) {
        throw std::runtime_error("[input_files] is not a table in the TOML file");
    }

    for (const auto& [key, value] : *input_files.as_table()) {
        std::string path = value.value<std::string>().value_or("");
        if (!path.empty()) {
            path = working_dir / path;
            input_file_paths.emplace(key, path);
        }
    }

    for (auto& [key, path] : input_file_paths) {
        logInputFile(path);
    }
}

void ClickHouseLogger::logInputFile(const std::filesystem::path& path) {
    logFile(path, "InputFiles");
}

void ClickHouseLogger::logOutputFile(const std::filesystem::path& path) {
    logFile(path, "OutputFiles");
}

void ClickHouseLogger::logFile(const std::filesystem::path& path, const std::string& table_name) {
    std::ifstream file(path);
    if (!file.is_open()) {
        spdlog::warn("Could not open file {}, it will thus not be saved to db", path.c_str());
        return;
    }

    std::stringstream ss;
    ss << file.rdbuf();
    std::string file_content = ss.str();

    std::filesystem::path relative_path = std::filesystem::relative(path, config_path_.parent_path());

    if (saved_paths_[table_name].contains(relative_path))
        return;  // Avoid logging several times the same file
    saved_paths_.at(table_name).insert(relative_path);

    ClickHouseBinaryBuffer buffer;
    spdlog::trace("Logging file {} to clickhouse", relative_path.c_str());
    serialize(buffer, relative_path.c_str(), file_content);

    pushBuffer(buffer, table_name);
}

void ClickHouseLogger::fetch_input_files_from_simulation_id(const std::string& simulation_id) {
    // Fetch list of files
    std::string list_query = fmt::format("SELECT input_file FROM `{}`.InputFiles FORMAT RowBinary", simulation_id);

    CURL* curl = curl_easy_init();
    if (!curl) throw std::runtime_error("curl init failed");

    ClickHouseBinaryReader list_reader(getBuffer(curl, list_query));

    std::vector<std::string> files;
    while (list_reader.peek() != EOF) {
        std::string path;
        list_reader.deserialize(path);
        files.push_back(path);
    }

    // Fetch all files individually
    for (const auto& relative_path : files) {
        std::string file_query = fmt::format("SELECT content FROM `{}`.InputFiles WHERE input_file = '{}' FORMAT RowBinary", simulation_id, relative_path);

        ClickHouseBinaryReader file_reader(getBuffer(curl, file_query));

        std::string content;
        file_reader.deserialize(content);

        std::filesystem::path out_dir = "/tmp/" + simulation_id;
        std::filesystem::path destination = out_dir / relative_path;
        std::filesystem::create_directories(destination.parent_path());

        spdlog::info("Downloading {} from ClickHouse and writing to {}", relative_path, destination.string());

        std::ofstream ofs(destination, std::ios::binary);
        ofs.write(content.data(), content.size());
    }

    curl_easy_cleanup(curl);
}

void ClickHouseLogger::saveDump(const std::string& dump_name, double time, const std::string& bin) {
    std::ostringstream ss;

    ss << "CREATE TABLE IF NOT EXISTS " << getFullTableName(dump_name)
        << " (time Float64, dump String) ENGINE = MergeTree() ORDER BY (time)";
    auto response = execQuery(ss.str());
    ss.str("");

    ClickHouseBinaryBuffer buffer;
    serialize(buffer, time, bin);
    pushBuffer(buffer, dump_name);
}

std::string ClickHouseLogger::loadDump(const std::string& dump_name, double time) {
    std::ostringstream ss;

    ss << "SELECT dump from `" + base_db_name_ + "`.`" + dump_name + "`"
        << " WHERE time = " << time << " FORMAT RowBinary";

    std::lock_guard<std::mutex> lock(curl_mutex_);  // Only one thread can access a given CURL instance at a time

    auto buffer = getBuffer(curl_, ss.str());

    if (buffer.size() <= 0)
        throw std::runtime_error("Attempted to load dump " + dump_name + " at time " + std::to_string(time) + ", but it does not seem to exist.");

    ClickHouseBinaryReader reader(std::move(buffer));
    std::string dump;
    reader.deserialize(dump);

    return dump;
}
