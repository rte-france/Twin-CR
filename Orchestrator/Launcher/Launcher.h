/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/


#ifndef LAUNCHER_H
#define LAUNCHER_H

#include "AssetSimulator.h"
#include "ClickHouseLogger.h"
#include "CycosimInterface.h"
#include "DSLEngine.h"
#include "DSLWebInterface.h"
#include "DynawoInterface.h"
#include "GameMasterInterface.h"
#include "HmiInterface.h"
#include "InformationFlowModel.h"
#include "ProcessLauncher.h"
#include "Replay.h"
#include "ScenarioHandler.h"

#include <filesystem>
#include <optional>
#include <string>

/**
 * Launcher class
 */
class Launcher {
    public:
        Launcher();

        ~Launcher();

        void init_from_toml(const std::filesystem::path& config_path, const std::optional<std::string> simulation_id, bool save_input_files = true, const std::string& base_db_name = "", std::optional<double> start_time = std::nullopt);

        void init_replay(const std::filesystem::path& config_path, const std::string& simulation_id);

        void init_from_clickhouse();

        void init_from_nats_config_path();

        /**
         * Start the simulation
         */
        void start();

        /**
         * Waits for a start signal from the nats server, then start the simulation
         */
        void start_from_nats();

        /**
         * Launch a replay
         */
        void start_replay();

        /**
         * Cleanup at the end of the simulation
         */
        void cleanup();

        std::string mode_;
        std::string simulation_id_;
        double end_time_;
        natsConnection* nats_connection_;
        natsSubscription* nats_subscription_;
        // Use std::optional to avoid default construction + all submodules are actually somewhat optional
        std::optional<Replay> replay_;
        std::optional<ClickHouseLogger> logger_;
        std::optional<InformationFlowModel> information_flow_model_;
        std::optional<ProcessLauncher> dynawo_process_launcher_;
        std::optional<DynawoInterface> dynawo_interface_;
        std::optional<AssetSimulator> asset_simulator_;
        std::optional<ScenarioHandler> scenario_handler_;
        std::optional<DSLEngine> dsl_engine_;
        std::optional<DSLWebInterface> dsl_web_interface_;
        std::optional<HMIInterface> hmi_interface_;
        std::optional<GameMasterInterface> game_master_interface_;
        std::optional<CycosimInterface> cycosim_interface_;
};

#endif // LAUNCHER_H
