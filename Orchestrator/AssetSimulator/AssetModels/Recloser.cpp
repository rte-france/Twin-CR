/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Recloser.h"
#include "EventQueue.h"
#include "Information.h"
#include "Orchestrator.h"

#include <spdlog/spdlog.h>


Recloser::Recloser(const std::string& line_name, std::vector<double>& opening_times, std::vector<double>& closing_times) {
    initialize(line_name, opening_times, closing_times);
}

Recloser::Recloser(const nlohmann::json::basic_json::value_type& config) {
    try {
        std::string line_name = config["line_name"];
        std::vector<double> opening_times = config["opening_times"];
        std::vector<double> closing_times = config["closing_times"];

        initialize(line_name, opening_times, closing_times);

    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid recloser config: " + std::string(e.what()) + " in:\n" + config.dump());
    }
}

void Recloser::initialize(const std::string& line_name, std::vector<double>& opening_times, std::vector<double>& closing_times) {
    line_name_ = line_name;
    closing_times_ = closing_times;
    opening_times_ = opening_times;

    for (auto& opening_time : opening_times) {
        if (Orchestrator::get().getCurrentTime() < opening_time) {
            Orchestrator::get().scheduleEvent(
                opening_time,
                makeCallback<&Recloser::openLine>(this)
            );
        } else {
            spdlog::warn("Fake opening of line {} at time {} skipped as it it before the current time {}",
                line_name, opening_time, Orchestrator::get().getCurrentTime());
        }
    }

    for (auto& closing_time : closing_times) {
        if (Orchestrator::get().getCurrentTime() < closing_time) {
            Orchestrator::get().scheduleEvent(
                closing_time,
                makeCallback<&Recloser::closeLine>(this)
            );
        } else {
            spdlog::warn("Fake closing of line {} at time {} skipped as it it before the current time {}",
                line_name, closing_time, Orchestrator::get().getCurrentTime());
        }
    }
}

void Recloser::openLine() {
    nlohmann::json j = {
        {"time", Orchestrator::get().getCurrentTime()},
        {"modelName", line_name_},
        {"message", "LINE : opening both sides"}
    };
    std::string event_string = j.dump();
    spdlog::info("Fake opening of line {}", line_name_);
    Orchestrator::get().emit(DynawoTimelineEvent(event_string));
}


void Recloser::closeLine() {
    nlohmann::json j = {
        {"time", Orchestrator::get().getCurrentTime()},
        {"modelName", line_name_},
        {"message", "LINE : closing both sides"}
    };
    std::string event_string = j.dump();
    spdlog::info("Fake closing of line {}", line_name_);
    Orchestrator::get().emit(DynawoTimelineEvent(event_string));
}
