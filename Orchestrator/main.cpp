/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Credentials.h"
#include "Launcher.h"

#include <spdlog/spdlog.h>
#include <toml++/impl/parser.hpp>

#include <optional>
#include <stdexcept>

enum class LauncherMode {
    NoSet,
    Toml,
    Nats,  // Deprecated
    Clickhouse,
    Replay
};

struct Arguments {
    LauncherMode mode = LauncherMode::NoSet;
    std::filesystem::path config_toml;
    std::string simulation_name;
    std::optional<std::string> credentials_toml;
};

int main(int argc, char* argv[]) {
    // Manually set log level as toml is not yet specified
    spdlog::set_level(spdlog::level::from_str("debug"));

    // Always flush
    spdlog::flush_on(spdlog::level::trace);

    Arguments args;
    int argument_count = argc - 1;
    if (argument_count <= 0) {
        throw std::runtime_error("Must specify either --from-toml, --replay, --from-clickhouse, or --from-nats");
    }
    argv++;  // Skip first argument (program name, not an argument)

    for (int i = 0; i < argument_count; i++) {
        std::string option = argv[i];
        if (option == "--from-toml") {
            if (argument_count > i + 1) {
                args.mode = LauncherMode::Toml;
                i++;
                args.config_toml = argv[i];
            } else {
                throw std::invalid_argument("Must specify config_path after --from-toml");
            }
        } else if (option == "--replay") {
            if (argument_count > i + 2) {
                args.mode = LauncherMode::Replay;
                i++;
                args.config_toml = argv[i];
                i++;
                args.simulation_name = argv[i];
            } else {
                throw std::invalid_argument("Must specify config_path and the name of the simulation to be replayed after --replay");
            }
        } else if (option == "--from-clickhouse") {
            args.mode = LauncherMode::Clickhouse;
        } else if (option == "--from-nats") {
            args.mode = LauncherMode::Nats;
        } else {
            throw std::invalid_argument("Unknown argument: " + option);
        }
    }

    Credentials::load_credentials();
    Launcher launcher;

    try {
        switch (args.mode) {
            case LauncherMode::NoSet:
                throw std::runtime_error("Must specify either --from-toml, --replay, --from-clickhouse, or --from-nats");
            case LauncherMode::Toml:
                launcher.init_from_toml(args.config_toml, std::nullopt);
                break;
            case LauncherMode::Nats:
                launcher.init_from_nats_config_path();
                break;
            case LauncherMode::Clickhouse:
                launcher.init_from_clickhouse();
                break;
            case LauncherMode::Replay:
                launcher.init_replay(args.config_toml, args.simulation_name);
                break;
        }

        switch (args.mode) {
            case LauncherMode::NoSet:
                throw std::runtime_error("Must specify either --from-toml, --replay, --from-clickhouse, or --from-nats");
            case LauncherMode::Toml:
                launcher.start();
                break;
            case LauncherMode::Nats:
            case LauncherMode::Clickhouse:
                launcher.start_from_nats();
                break;
            case LauncherMode::Replay:
                launcher.start_replay();
                break;
        }
    } catch (const std::exception& e) {
        spdlog::critical("Simulation aborted: {}", e.what());
        launcher.cleanup();
        return 1;
    } catch (...) {
        spdlog::critical("Simulation aborted on a non-standard exception");
        launcher.cleanup();
        return 1;
    }

    return 0;
}
