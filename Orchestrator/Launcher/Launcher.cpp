/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Launcher.h"
#include "Broker.h"
#include "Credentials.h"
#include "DynawoHandlers/XmlHandler.h"
#include "InteractiveReplayHandler.h"
#include "Orchestrator.h"
#include "../utils/EnvironmentVariable.h"
#include "../utils/TomlExtension.h"

#include <curl/curl.h>
#include "nlohmann/detail/exceptions.hpp"
#include <toml++/impl/parser.hpp>

#include <cstdint>
#include <exception>
#include <filesystem>
#include <optional>
#include <spdlog/spdlog.h>
#include <stdexcept>

const int64_t TIMEOUT = 60 * 60 * 1000 * 24;  // 24 hour

Launcher::Launcher() {
    if (natsConnection_ConnectTo(&nats_connection_, Credentials::get().getNatsURL()) != NATS_OK)
        throw std::runtime_error("Failed to connect to NATS");

    if (natsConnection_SubscribeSync(&nats_subscription_, nats_connection_, "Start") != NATS_OK)
        throw std::runtime_error("Failed to subscribe to 'Start'");
}

Launcher::~Launcher() {
    if (dynawo_interface_) {
        // Must be called before temp files are deleted
        dynawo_interface_->logOutputFiles();
    }

    if (mode_ == "clickhouse") {
        // Delete temporary files
        if (simulation_id_.find("..") != std::string::npos) {
            spdlog::warn("Simulation id {} looks like a relative path, skipping temp file cleanup", simulation_id_);
            return;
        }
        std::filesystem::path temp_files = "/tmp/" + simulation_id_;
        spdlog::info("Deleting temporary files in {}", temp_files.string());
        std::filesystem::remove_all(temp_files);
    }

    natsSubscription_Destroy(nats_subscription_);
    natsConnection_Destroy(nats_connection_);
    spdlog::info("Simulation {} completed", simulation_id_);
}

void Launcher::init_from_toml(const std::filesystem::path& config_path, const std::optional<std::string> simulation_id, bool save_input_files, const std::string& base_db_name, std::optional<double> start_time) {
    if (mode_.empty()) {
        mode_ = "toml";
    }
    toml::table config = toml::parse_file(config_path.c_str());
    std::filesystem::path working_dir = config_path.parent_path();
    std::filesystem::path job_file = working_dir / get_or_throw<std::string>(config, {"input_files", "job_file"});

    std::string log_level = config["log_level"].value_or("INFO");
    std::transform(log_level.begin(), log_level.end(), log_level.begin(), ::tolower);
    spdlog::set_level(spdlog::level::from_str(log_level));

    // Dynawo process launcher, must be created at the very start before any other threads are created.
    // Must not be recreated when retrying after a failed init (safe to reuse since the subprocess is only given its command on Launcher::start())
    if (!dynawo_process_launcher_.has_value()) {
        dynawo_process_launcher_.emplace();
    }

    JobHandler job_handler = JobHandler(job_file);
    double dynawo_start_time = job_handler.getStartTime();
    double actual_start_time;
    bool from_dump;
    if (start_time.has_value()) {
        actual_start_time = start_time.value();
        from_dump = true;
    } else {
        actual_start_time = dynawo_start_time;
        from_dump = false;
    }
    end_time_ = job_handler.getStopTime();

    Orchestrator::create(working_dir, config, actual_start_time, end_time_, simulation_id);
    simulation_id_ = Orchestrator::get().getSimulationName();

    // Create information logger
    logger_.emplace(config_path, base_db_name, actual_start_time, save_input_files);
    // auto logger = ClickHouseLogger(config_path, "sim_2025_08_27_16_54_46", 5);

    // Load cycosim config if specified
    std::optional<std::string> cycosim_config_file_str = get_or_continue<std::string>(config, {"input_files", "cycosim_integration_file"});
    std::optional<nlohmann::json> cycosim_config;
    if (cycosim_config_file_str.has_value()) {
        std::filesystem::path cycosim_config_file = working_dir / cycosim_config_file_str.value();

        std::ifstream config_stream(cycosim_config_file);
        if (!config_stream.is_open()) {
            throw std::runtime_error("CycosimInterface: Failed to open config file: " + cycosim_config_file.string());
        }
        try {
            cycosim_config = nlohmann::json::parse(config_stream);
        } catch (const std::exception& e) {
            throw std::runtime_error(fmt::format("Could not parse JSON Cycosim integration file: {}, error: {}", cycosim_config_file.string(), e.what()));
        }
    }

    // Create information flow model
    if (from_dump) {
        information_flow_model_.emplace(*logger_, actual_start_time);
        asset_simulator_.emplace(*logger_, actual_start_time);
    } else {
        information_flow_model_.emplace(true, *logger_, cycosim_config);
        asset_simulator_.emplace(*information_flow_model_, *logger_);
    }
    // {
    //     auto start = std::chrono::steady_clock::now();
    //     std::ostringstream os(std::ios::binary);  // std::ofstream os("ifl.bin", std::ios::binary);
    //     ser20::BinaryOutputArchive archive(os);
    //     archive(information_flow_model);
    //     std::cout << "IFL dump time: " << std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - start).count() << " µs" << std::endl;
    // }
    // auto deserialized_ifl = InformationFlowModel("ifl.bin");

    // Initialize the broker (automatically launches the performance broker)
    Broker::get().init();

    // Initialize Cycosim interface if configured
    if (cycosim_config.has_value()) {
        if (from_dump) {
            throw std::invalid_argument("Save/load functionnality not implemented for the Cycosim interface");
        }
        spdlog::info("Creating CycosimInterface...");
        cycosim_interface_.emplace(cycosim_config.value(), *information_flow_model_);
        spdlog::info("CycosimInterface created successfully");
    } else {
        spdlog::warn("No cycosim integration file specified - cycosim disabled");
    }

    // Initialise Dynawo interface
    dynawo_interface_.emplace(*information_flow_model_, dynawo_start_time, actual_start_time, end_time_, *logger_, *dynawo_process_launcher_, save_input_files);

    // Initialise the scenario handler
    scenario_handler_.emplace(*information_flow_model_, *dynawo_interface_, actual_start_time);

    // Initialise the DSL engine
    if (isEnvironmentVariableTrue("WITH_LEGACY_DSL")) {
        spdlog::info("WITH_LEGACY_DSL is set: the C++ DSL engine and its web interface are disabled, using the Python gamemaster instead");
    } else {
        if (from_dump) {
            dsl_engine_.emplace(*scenario_handler_, *dynawo_interface_, *logger_, actual_start_time);
        } else {
            dsl_engine_.emplace(true, *scenario_handler_, *dynawo_interface_, *logger_, actual_start_time);
        }
        dsl_web_interface_.emplace(*dsl_engine_);
    }

    // Initialise HMI interface
    hmi_interface_.emplace(*information_flow_model_, *scenario_handler_, *logger_);

    // Initialise the Game master interface
    game_master_interface_.emplace(*scenario_handler_, *logger_);
}

void Launcher::init_replay(const std::filesystem::path& config_path, const std::string& simulation_id) {
    if (mode_.empty()) {
        mode_ = "toml";
    }

    // TODO: get input files from db instead

    toml::table config = toml::parse_file(config_path.c_str());
    std::filesystem::path working_dir = config_path.parent_path();
    std::filesystem::path job_file = working_dir / get_or_throw<std::string>(config, {"input_files", "job_file"});

    std::string log_level = config["log_level"].value_or("INFO");
    std::transform(log_level.begin(), log_level.end(), log_level.begin(), ::tolower);
    spdlog::set_level(spdlog::level::from_str(log_level));

    JobHandler job_handler = JobHandler(job_file);
    double start_time = job_handler.getStartTime();
    end_time_ = job_handler.getStopTime();

    Orchestrator::create(working_dir, config, start_time, end_time_, simulation_id);
    simulation_id_ = simulation_id;

    // Initialize the replay
    replay_.emplace();

    // Initialize the broker (automatically launches the performance broker)
    Broker::get().init();

    // Create information flow model (without subscriptions as it will perform no work, only needed as a dependency of the HMI interface)
    information_flow_model_.emplace(false, *logger_, std::nullopt);

    std::optional<std::string> cycosim_config_file_str = get_or_continue<std::string>(config, {"input_files", "cycosim_integration_file"});
    if (cycosim_config_file_str.has_value()) {
        throw std::invalid_argument("Replay of simulations including a cycosim_integration_file not yet implemented");
    }

    // Initialise the scenario handler
    scenario_handler_.emplace(*information_flow_model_, *dynawo_interface_);
}

void Launcher::init_from_clickhouse() {
    spdlog::info("Waiting for simulation id to be specified via NATS server on topic 'Start'...");

    // Create a file to be used for docker-compose healthcheck
    try {
        std::ofstream healthcheck_file("/tmp/orchestrator_healthcheck");
        if (healthcheck_file.is_open()) {
            healthcheck_file << "OK";
            healthcheck_file.close();
        } else {
            spdlog::warn("Could not create healthcheck file at /tmp/orchestrator_healthcheck");
        }
    } catch (const std::exception& e) {
        spdlog::warn("Exception creating healthcheck file: {}", e.what());
    }

    mode_ = "clickhouse";

    std::string status;
    do {
        natsMsg *msg = nullptr;
        if (natsSubscription_NextMsg(&msg, nats_subscription_, TIMEOUT) != NATS_OK)
            throw std::runtime_error("Timeout waiting for simulation ID");

        std::string message(natsMsg_GetData(msg), natsMsg_GetDataLength(msg));
        spdlog::debug("Received {} from nats", message);

        std::filesystem::path config_path;
        std::optional<double> start_time;
        bool valid_message = true;
        std::string simulation_id;

        try {
            nlohmann::json payload = nlohmann::json::parse(message);
            simulation_id = payload["simulation_id"];
            config_path = payload["config_path"].get<std::string>();
            if (payload.contains("start_time"))
                start_time = payload["start_time"].get<double>();

        } catch (const nlohmann::json::parse_error& e) {
            status = "Could not parse message (invalid JSON)\n" + message;
            valid_message = false;
        } catch (const nlohmann::json::type_error& e) {
            status = "Missing or invalid 'simulation_id' or 'config_path' in message";
            valid_message = false;
        }

        if (valid_message) {
            try {
                ClickHouseLogger::fetch_input_files_from_simulation_id(simulation_id);

                bool save_input_files = false;  // Don't need to save input files as they already come from clickhouse

                if (start_time.has_value()) {
                    // Start the simulation from the dump of a previous one
                    init_from_toml(config_path, std::nullopt, save_input_files, simulation_id, start_time);
                } else {
                    // Start new simulation from scratch
                    config_path = ("/tmp/" + simulation_id) / config_path;
                    init_from_toml(config_path, simulation_id, save_input_files);
                }

                status = "READY";
            } catch (const std::exception &e) {
                status = e.what();
            }
        }

        nlohmann::json response;
        response["status"] = status;
        // Send response
        const char* reply = natsMsg_GetReply(msg);
        if (reply != nullptr) {
            natsConnection_PublishString(nats_connection_, reply, response.dump(4).c_str());
        }
        natsMsg_Destroy(msg);

        if (status != "READY") {
            spdlog::warn(status);
            spdlog::warn("Failed to initialize from clickhouse, retrying...");
        }
    } while (status != "READY");
}

void Launcher::init_from_nats_config_path() {
    spdlog::critical("Deprecated option");
    spdlog::warn("Waiting for path to be specified via NATS server...");

    // Create a file to be used for docker-compose healthcheck
    try {
        std::ofstream healthcheck_file("/tmp/orchestrator_healthcheck");
        if (healthcheck_file.is_open()) {
            healthcheck_file << "OK";
            healthcheck_file.close();
        } else {
            spdlog::warn("Could not create healthcheck file at /tmp/orchestrator_healthcheck");
        }
    } catch (const std::exception& e) {
        spdlog::warn("Exception creating healthcheck file: {}", e.what());
    }

    mode_ = "nats";

    std::string status;
    do {
        natsMsg *msg = nullptr;
        if (natsSubscription_NextMsg(&msg, nats_subscription_, TIMEOUT) != NATS_OK)
            throw std::runtime_error("Timeout waiting for config path");

        std::string message(natsMsg_GetData(msg), natsMsg_GetDataLength(msg));
        spdlog::debug("Received {} from nats", message);

        bool valid_message = true;
        std::filesystem::path config_path;
        try {
            nlohmann::json payload = nlohmann::json::parse(message);
            config_path = payload["config_path"].get<std::string>();
        } catch (const nlohmann::json::parse_error& e) {
            status = "Could not parse message (invalid JSON)\n" + message;
            valid_message = false;
        } catch (const nlohmann::json::type_error& e) {
            status = "Missing or invalid 'config_path' in message";
            valid_message = false;
        }

        if (valid_message) {
            try {
                spdlog::info("Initializing simulation with config {}", config_path.string());
                init_from_toml(config_path, std::nullopt);
                status = "READY";
            } catch (const std::exception &e) {
                status = e.what();
            }
        }

        nlohmann::json response;
        response["status"] = status;
        if (status == "READY") {
            response["simulation_id"] = Orchestrator::get().getSimulationName();
        }

        // Send response
        const char* reply = natsMsg_GetReply(msg);
        if (reply != nullptr) {
            natsConnection_PublishString(nats_connection_, reply, response.dump(4).c_str());
        }
        natsMsg_Destroy(msg);

        if (status != "READY") {
            spdlog::warn(status);
            spdlog::warn("Failed to initialize from nats, retrying...");
        }
    } while (status != "READY");
}

void Launcher::start() {
    spdlog::info("Starting simulation {}", simulation_id_);
    Orchestrator::get().run(std::nullopt);

    // Cleanup once simulation is completed
    cleanup();
}

void Launcher::start_from_nats() {
    std::string status;
    do {
        natsMsg *msg = nullptr;
        if (natsSubscription_NextMsg(&msg, nats_subscription_, TIMEOUT) != NATS_OK)
            throw std::runtime_error("Timeout waiting for start signal");

        std::string message(natsMsg_GetData(msg), natsMsg_GetDataLength(msg));
        spdlog::debug("Received {} from nats", message);

        try {
            nlohmann::json payload = nlohmann::json::parse(message);
            std::string command = payload["command"];
            if (command == "start") {
                status = "STARTED";
            } else {
                status = "Invalid command (expected 'start')";
            }
        } catch (const nlohmann::detail::type_error& e) {
            status = "Could not parse message: " + std::string(e.what()) + " in:\n" + message;
        } catch (const std::exception &e) {
            status = e.what();
        }

        nlohmann::json response;
        response["status"] = status;
        response["simulation_id"] = Orchestrator::get().getSimulationName();
        // Send response
        const char* reply = natsMsg_GetReply(msg);
        if (reply != nullptr) {
            natsConnection_PublishString(nats_connection_, reply, response.dump(4).c_str());
        }
        natsMsg_Destroy(msg);

        if (status != "STARTED") {
            spdlog::warn("Failed to start from nats, retrying...");
        }
    } while (status != "STARTED");

    start();
}

void Launcher::start_replay() {
    if (!replay_.has_value()) throw std::runtime_error("Trying to start replay without first initializing it");
    auto replay_handler = InteractiveReplayHandler(*replay_, end_time_);
    replay_handler.start_interactive_session();
}

void Launcher::cleanup() {
    // Ensure Clickhouse has received all data before letting the Broker send the stop signal
    // This avoid relying on destruction order of the logger and broker (although it is currently correct)
    if (logger_.has_value()) {
        logger_->cleanup();
    }
}
