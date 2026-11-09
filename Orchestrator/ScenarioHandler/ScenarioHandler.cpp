/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "ScenarioHandler.h"
#include "Broker.h"
#include "EventQueue.h"
#include "Information.h"
#include "InformationFlowModel.h"
#include "Orchestrator.h"
#include "../utils/TomlExtension.h"
#include "SignalHandler.h"

#include <chrono>
#include <optional>
#include <stdexcept>

ScenarioHandler::ScenarioHandler(InformationFlowModel& information_flow_model, DynawoInterface& dynawo_interface, double start_time) :
broker_(Broker::get()),
information_flow_model_(information_flow_model),
dynawo_interface_(dynawo_interface),
start_time_(start_time) {
    auto& working_dir = Orchestrator::get().getWorkingDir();
    auto& config = Orchestrator::get().getConfig();

    auto scenario_name = get_or_continue<std::string>(config, {"input_files", "scenario_file"});
    if (!scenario_name) {
        spdlog::info("No input_files.scenario_file in config.toml, starting with no scheduled scenario");
        return;
    }

    std::filesystem::path scenario_file = working_dir / *scenario_name;
    if (!std::filesystem::exists(scenario_file)) {
        throw std::invalid_argument(fmt::format("Scenario file {} given in config.toml does not exist", scenario_file.string()));
    }

    auto scenarios = nlohmann::json::parse(std::ifstream(scenario_file));

    for (const auto& scenario : scenarios) {
        applyScenario(scenario);
    }
}

/**
 * Emit the signal straight away if it is due for now and the caller is the simulation thread (direct emission from other threads if forobidden), else schedule it.
 */
template <typename Information>
static void emitNowOrLater(Information signal, double t_start) {
    if (t_start <= Orchestrator::get().getCurrentTime() && Orchestrator::get().isMainThread()) {
        Orchestrator::get().emit(signal);
    } else {
        Orchestrator::get().emitLater(std::move(signal), t_start);
    }
}

nlohmann::json ScenarioHandler::applyScenario(const nlohmann::json& scenario, Mode mode) {
    nlohmann::json reply;
    reply["status"] = "OK";

    // Note: scenarios can be added during the simulation via the GameMasterInterface, so all functions calls defined here should be thread-safe
    if (spdlog::should_log(spdlog::level::trace)) {
        spdlog::trace("ScenarioHandler received command {}\nto {}", scenario.dump(4), to_string(mode));
    }

    try {
        std::string scenario_type = scenario["command"];

        double t_start;
        if (scenario.contains("t_start")) {
            t_start = scenario["t_start"];
        } else if (scenario.contains("t_start_from_now")) {
            t_start = scenario["t_start_from_now"];
            t_start += Orchestrator::get().getCurrentTime();
        } else {
            t_start = Orchestrator::get().getCurrentTime();
        }

        if(t_start < start_time_) {
            std::string err = fmt::format("Skipping scenario command scheduled for time {}, which is before start time {}", t_start, start_time_);
            spdlog::warn(err);
            reply["status"] = err;

        } else if (scenario_type == "pause") {
            if (mode == Mode::Execute) {
                Orchestrator::get().scheduleEventOrNow(
                    t_start,
                    makeCallback<&Orchestrator::pause>(&Orchestrator::get())
                );
            }

        } else if (scenario_type == "stop") {
            if (mode == Mode::Execute) {
                Orchestrator::get().scheduleEventOrNow(
                    t_start,
                    makeCallback<&SignalHandler::interrupt>()
                );
            }

        } else if (scenario_type == "resume") {
            if (t_start > Orchestrator::get().getCurrentTime()) {
                reply["status"] = "Error: cannot schedule unpausing the simulation at a future time, since time does not advance when paused";
                return reply;
            }
            if (mode == Mode::Execute) {
                Orchestrator::get().resume();
            }

        } else if (scenario_type == "fast_forward") {
            if (mode == Mode::Execute) {
                Orchestrator::get().scheduleEventOrNow(
                    t_start,
                    makeCallback<&Orchestrator::fastForward>(&Orchestrator::get())
                );
            }

        } else if (scenario_type == "command_injection") {
            // Control signal sent through the information flow model
            std::string command_id = scenario["command_id"];
            double value = scenario["value"];
            std::string source = scenario["source"];
            std::string destination = scenario["destination"];
            auto path = information_flow_model_.getPath(source, destination);
            std::string topic = "HMI";
            if (mode == Mode::Execute) {
                auto control_signal = ControlSent(command_id, value, t_start, destination, path, topic, std::nullopt, information_flow_model_.nextControlUid());
                emitNowOrLater(std::move(control_signal), t_start);
            }

        } else if (scenario_type == "command_injection_received") {
            // Control signal directly sent to its destination
            std::string command_id = scenario["command_id"];
            double value = scenario["value"];
            std::string destination = scenario["destination"];
            std::string topic = scenario["topic"];
            if (mode == Mode::Execute) {
                auto control_signal = ControlReceived(command_id, value, t_start, destination, topic, std::nullopt, information_flow_model_.nextControlUid());
                emitNowOrLater(std::move(control_signal), t_start);
            }

        } else if (scenario_type == "command_injection_game_master") {
            // Control signal as sent by the game master
            std::string command_id = scenario["command_id"];
            double value = scenario["value"];
            std::string topic = "GameMaster";
            auto control_signal = ActualControl(command_id, value, t_start, topic);

            if (mode == Mode::Execute) emitNowOrLater(std::move(control_signal), t_start);

        } else if (scenario_type == "iidm_command") {
            // Send a command based on an iidm_id, an attribute (P, Q, state), and the type of the IIDM element
            std::string iidm_id = scenario["iidm_id"];
            double value = scenario["value"];
            std::string attribute = scenario["attribute"];
            std::string topic = "GameMaster";
            std::string command_id = dynawo_interface_.getInputFromIidm(iidm_id, attribute);

            auto control_signal = ActualControl(command_id, value, t_start, topic);

            if (mode == Mode::Execute) emitNowOrLater(std::move(control_signal), t_start);

        } else if (scenario_type == "dynamic_model_command") {
            // Send a command to a purely dynamic model
            std::string dynamic_model = scenario["dynamic_model"];
            double value = scenario["value"];
            std::string attribute = scenario["attribute"];
            std::string topic = "GameMaster";
            std::string command_id = dynawo_interface_.getInputFromDynamicModel(dynamic_model, attribute);

            auto control_signal = ActualControl(command_id, value, t_start, topic);

            if (mode == Mode::Execute) emitNowOrLater(std::move(control_signal), t_start);

        } else if (scenario_type == "dynamic_model_scale_multiplier") {
            // scale_multiplier for a purely dynamic model
            std::string dynamic_model = scenario["dynamic_model"];
            std::string attribute = scenario["attribute"];
            double multiplier_increase = scenario["multiplier_increase"];
            std::string command_id = dynawo_interface_.getInputFromDynamicModel(dynamic_model, attribute);

            if (mode == Mode::Execute) {
                if (t_start <= Orchestrator::get().getCurrentTime() && Orchestrator::get().isMainThread()) {
                    dynawo_interface_.scaleMultiplierBy(command_id, multiplier_increase);
                } else {
                    Orchestrator::get().scheduleEvent(
                        t_start,
                        makeCallback<&DynawoInterface::scaleMultiplierBy>(&dynawo_interface_, command_id, multiplier_increase)
                    );
                }
            }

        } else if (scenario_type == "scale_multiplier") {
            // Increase the multiplier of a Dynawo Updatable (UpdatableDiscrete/UpdatableContinuous)
            // Logs a warning if the Dynawo variable is not connected via UpdatableDiscrete/UpdatableContinuous
            // (in the future, all Dynawo connections will have this functionality)
            std::string iidm_id = scenario["iidm_id"];
            std::string attribute = scenario["attribute"];
            double multiplier_increase = scenario["multiplier_increase"];
            std::string command_id = dynawo_interface_.getInputFromIidm(iidm_id, attribute);

            if (mode == Mode::Execute) {
                if (t_start <= Orchestrator::get().getCurrentTime() && Orchestrator::get().isMainThread()) {
                    dynawo_interface_.scaleMultiplierBy(command_id, multiplier_increase);
                } else {
                    Orchestrator::get().scheduleEvent(
                        t_start,
                        makeCallback<&DynawoInterface::scaleMultiplierBy>(&dynawo_interface_, command_id, multiplier_increase)
                    );
                }
            }

        } else if (scenario_type == "manual_actuator_scada") {
            // Sends a TS from the SCADA to itself
            std::string command_id = scenario["command_id"];
            double value = scenario["value"];
            std::string topic = scenario["topic"];
            auto& config = Orchestrator::get().getConfig();
            auto scada_location = get_or_throw<std::string>(config, {"hmi", "location"});
            auto control_signal = MeasurementSent(command_id, value, t_start,
                scada_location, information_flow_model_.getPath(scada_location, scada_location), topic, std::nullopt);

            if (mode == Mode::Execute) emitNowOrLater(std::move(control_signal), t_start);

        } else if (scenario_type == "change_network_characteristics") {
            // Modification of the information flow model (delay, drop, and/or corruption function)
            auto nodes = scenario.value("nodes", nlohmann::json::array());  // Defaults to empty list if not specified
            auto links = scenario.value("links", nlohmann::json::array());

            for (const auto& node : nodes) {
                std::string node_name = node;

                if (mode == Mode::Execute) {  // Schedule execution for t_start
                    if (t_start <= Orchestrator::get().getCurrentTime()) {  // Ensures network characteristics are changed even if the orchestrator is paused
                        information_flow_model_.addCharacteristicsToNode(node_name, scenario, mode);
                    } else {
                        Orchestrator::get().scheduleEvent(
                            t_start,
                            makeCallback<&InformationFlowModel::addCharacteristicsToNode>(&information_flow_model_, node_name, scenario, mode)
                        );
                    }
                } else {  // Mode::Validate -> Validate now
                    information_flow_model_.addCharacteristicsToNode(node_name, scenario, mode);
                }
            }
            for (const auto& link : links) {
                std::string source = link["from"];
                std::string destination = link["to"];

                if (mode == Mode::Execute) {  // Schedule execution for t_start
                    if (t_start <= Orchestrator::get().getCurrentTime()) {  // Ensures network characteristics are changed even if the orchestrator is paused
                        information_flow_model_.addCharacteristicsToLink(source, destination, scenario, mode);
                    } else {
                        Orchestrator::get().scheduleEvent(
                            t_start,
                            makeCallback<&InformationFlowModel::addCharacteristicsToLink>(&information_flow_model_, source, destination, scenario, mode)
                        );
                    }
                } else {  // Mode::Validate -> Validate now
                    information_flow_model_.addCharacteristicsToLink(source, destination, scenario, mode);
                }
            }
        } else if (scenario_type == "get_link_characteristics") {
            std::string from = scenario["link"]["from"];
            std::string to = scenario["link"]["to"];
            reply["reply"] = information_flow_model_.getLinkConfig(from, to);

        } else if (scenario_type == "get_node_characteristics") {
            std::string node_name = scenario["node"];
            reply["reply"] = information_flow_model_.getNodeConfig(node_name);

        } else if (scenario_type == "get_path_characteristics") {
            std::string source = scenario["source"];
            std::string destination = scenario["destination"];
            reply["reply"] = information_flow_model_.getPathConfig(source, destination);

        } else if (scenario_type == "get_simulation_name") {
            reply["reply"] = Orchestrator::get().getSimulationName();

        } else if (scenario_type == "get_initial_clock_time") {
            auto duration_since_epoch = Orchestrator::get().getInitialClockTime().time_since_epoch();
            double seconds = std::chrono::duration_cast<std::chrono::duration<double>>(duration_since_epoch).count();
            reply["reply"] = seconds;

        } else if (scenario_type == "add_dsl_subscription") {
            std::string id = scenario["id"];
            if (mode == Mode::Execute) {
                broker_.add_dsl_subscription(id);
            }

        } else if (scenario_type == "add_dsl_subscription_from_iidm") {
            std::string iidm_id = scenario["iidm_id"];
            std::string attribute = scenario["attribute"];
            std::string output_id = dynawo_interface_.getOutputFromIidm(iidm_id, attribute);
            if (mode == Mode::Execute) {
                broker_.add_dsl_subscription(output_id);
            }
            reply["reply"] = output_id;

        } else if (scenario_type == "remove_dsl_subscription") {
            std::string id = scenario["id"];
            if (mode == Mode::Execute) {
                broker_.remove_dsl_subscription(id);
            }

        } else if (scenario_type == "remove_dsl_subscription_from_iidm") {
            std::string iidm_id = scenario["iidm_id"];
            std::string attribute = scenario["attribute"];
            std::string output_id = dynawo_interface_.getOutputFromIidm(iidm_id, attribute);
            if (mode == Mode::Execute) {
                broker_.remove_dsl_subscription(output_id);
            }
            reply["reply"] = output_id;

        } else {
            throw std::invalid_argument("Unknown scenario type: " + scenario_type);
        }

    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid scenario: " + std::string(e.what()) + " in:\n" + scenario.dump());
    }
    return reply;
}
