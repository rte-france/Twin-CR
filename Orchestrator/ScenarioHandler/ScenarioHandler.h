/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef SCENARIO_HANDLER_H
#define SCENARIO_HANDLER_H

#include "Broker.h"
#include "InformationFlowModel.h"
#include "DynawoInterface.h"
#include "../utils/ScenarioHandlerInterface.h"

#include <nlohmann/json.hpp>


/**
 * Class responsible for reading the scenario file and implementing the scenarios in the simulation
 */
class ScenarioHandler : public ScenarioHandlerInterface {
    public:
        ScenarioHandler(InformationFlowModel& information_flow_model, DynawoInterface& dynawo_interface, double start_time = 0);

        /**
         * Apply a scenario based on a JSON scenario
         * If mode is set to Validate, the JSON is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         * Returns string
         */
        nlohmann::json applyScenario(const nlohmann::json& scenario, Mode mode=Mode::Execute) override;

        std::vector<std::string> listNodes() override {
            return information_flow_model_.listNodes();
        }
        std::vector<std::string> listDestinations(const std::string& source) override {
            return information_flow_model_.listDestinations(source);
        }

    private:
        Broker& broker_;
        InformationFlowModel& information_flow_model_;
        DynawoInterface& dynawo_interface_;
        double start_time_;
        std::string scada_location_;
};

#endif // SCENARIO_HANDLER_H
