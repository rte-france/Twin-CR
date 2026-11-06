/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef RECORDING_SCENARIO_HANDLER_H
#define RECORDING_SCENARIO_HANDLER_H

#include "../utils/ScenarioHandlerInterface.h"

#include <unordered_map>
#include <vector>
#include "Orchestrator.h"


/**
 * A ScenarioHandlerInterface that records what it was asked to apply instead of applying it, stamping each command with the
 * simulation time it arrived at. The recording is what a test asserts on: it is exactly the stream of commands the
 * module under test would have handed the real ScenarioHandler.
 *
 * Only Mode::Execute is recorded. Mode::Validate is answered "OK" without being recorded, since validation runs at
 * load time and says nothing about what a run does; set a rejection with failValidationWhen() to test the other path.
 */
class RecordingScenarioHandler : public ScenarioHandlerInterface {
    public:
        using ValidationRule = std::function<std::string(const nlohmann::json&)>;

        nlohmann::json applyScenario(const nlohmann::json& scenario, Mode mode) override {
            if (mode == Mode::Validate) {
                std::string status = validation_rule_ ? validation_rule_(scenario) : "OK";
                return {{"status", status}};
            }
            applied_.push_back({
                {"t", Orchestrator::get().getCurrentTime()},
                {"command", scenario},
            });
            return {{"status", "OK"}};
        }

        void setNetwork(std::vector<std::string> nodes, std::unordered_map<std::string, std::vector<std::string>> links) {
            nodes_ = std::move(nodes);
            links_ = std::move(links);
        }

        std::vector<std::string> listNodes() override { return nodes_; }
        std::vector<std::string> listDestinations(const std::string& source) override {
            auto it = links_.find(source);
            return it == links_.end() ? std::vector<std::string>{} : it->second;
        }

        /**
         * Makes validation answer with something other than "OK" for the commands the rule selects, so a test can
         * check that the module rejects what the ScenarioHandler would have refused.
         */
        void failValidationWhen(ValidationRule rule) { validation_rule_ = std::move(rule); }

        /** Every Mode::Execute command, in order, as [{"t": <time>, "command": {...}}, ...]. */
        const nlohmann::json& applied() const { return applied_; }

    private:
        nlohmann::json applied_ = nlohmann::json::array();
        ValidationRule validation_rule_;
        std::vector<std::string> nodes_;
        std::unordered_map<std::string, std::vector<std::string>> links_;
};

#endif // RECORDING_SCENARIO_HANDLER_H
