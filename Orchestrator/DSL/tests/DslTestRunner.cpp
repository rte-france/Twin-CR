/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

/*
 * Runs one DSL regression case and compares what the engine did against a golden file.
 *
 * A case is a directory holding:
 *   script.dsl     the DSL the engine loads at startup
 *   expected.json  the golden recording, regenerated with --update
 *   case.toml      optional: duration, period, a command submitted mid-run (command_at/command),
 *                  measurements to feed when/when_rearming clauses (keyed by
 *                  iidm_id, or by dynamic_model for an output on a purely dynamic model), and a
 *                  reload_at / cancel_at / replace_at point, and partial statements to complete
 *
 * What is recorded is the stream of commands the engine hands its ScenarioHandlerInterface, each stamped with the
 * simulation time it was applied at. That is the engine's entire observable output, so a case pins down timing,
 * ordering, id resolution and payload shape at once, without Dynawo, NATS or ClickHouse.
 */

#include "DSLEngine.h"
#include "ExampleDynawoInterface.h"
#include "Information.h"
#include "Orchestrator.h"
#include "RecordingScenarioHandler.h"
#include "TmpDirClickHouseLogger.h"

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>
#include <toml++/toml.h>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <vector>


struct Measurement {
    double time = 0.0;
    std::string iidm_id;
    std::string dynamic_model;  // Set instead of iidm_id for an output on a purely dynamic model
    std::string attribute;
    double value = 0.0;
};

struct CaseSpec {
    double duration = 30.0;
    double period = 1.0;
    // When set, the engine is dumped at this time, thrown away, and rebuilt from the dump before the run continues.
    std::optional<double> reload_at;
    // When set, the run pauses here and cancels the one event whose description contains cancel_match.
    std::optional<double> cancel_at;
    std::string cancel_match;
    // Same, for the edit path: the matched event is replaced by replace_with, whose times are absolute.
    std::optional<double> replace_at;
    std::string replace_match;
    std::string replace_with;
    // DSL submitted mid-run the way the terminal does it, so 'at' and 'after' can be told apart: at t=0 they
    // resolve to the same instant, and only a later submission separates them.
    std::optional<double> command_at;
    std::string command;
    // Partially typed statements to ask the engine to complete, once the script is loaded
    std::vector<std::string> completions;
    std::vector<Measurement> measurements;
};

CaseSpec readCaseSpec(const std::filesystem::path& case_dir) {
    CaseSpec spec;
    auto path = case_dir / "case.toml";
    if (!std::filesystem::exists(path)) return spec;

    auto table = toml::parse_file(path.string());
    spec.duration = table["duration"].value_or(spec.duration);
    spec.period = table["period"].value_or(spec.period);
    if (auto reload_at = table["reload_at"].value<double>()) spec.reload_at = *reload_at;
    if (auto cancel_at = table["cancel_at"].value<double>()) spec.cancel_at = *cancel_at;
    spec.cancel_match = table["cancel_match"].value_or(std::string());
    if (auto replace_at = table["replace_at"].value<double>()) spec.replace_at = *replace_at;
    spec.replace_match = table["replace_match"].value_or(std::string());
    spec.replace_with = table["replace_with"].value_or(std::string());
    if (auto command_at = table["command_at"].value<double>()) spec.command_at = *command_at;
    spec.command = table["command"].value_or(std::string());
    if (auto* completions = table["completions"].as_array()) {
        for (auto& node : *completions) {
            if (auto partial = node.value<std::string>()) spec.completions.push_back(*partial);
        }
    }
    if (auto* measurements = table["measurements"].as_array()) {
        for (auto& node : *measurements) {
            auto* measurement = node.as_table();
            if (!measurement) continue;
            spec.measurements.push_back({
                (*measurement)["time"].value_or(0.0),
                (*measurement)["iidm_id"].value_or(std::string()),
                (*measurement)["dynamic_model"].value_or(std::string()),
                (*measurement)["attribute"].value_or(std::string()),
                (*measurement)["value"].value_or(0.0),
            });
        }
    }
    return spec;
}

/**
 * Cancel the single event whose describe() contains 'match', and report what happened so a golden can assert on it.
 * Only cancel one as listEvents() walks an unordered map, so a case that matches more than one event would have an unstable result;
 */
std::optional<nlohmann::json> findSingleEvent(DSLEngine& engine, const std::string& match) {
    std::vector<nlohmann::json> matched;
    for (auto& entry : engine.listEvents()) {
        if (entry.value("describe", std::string()).find(match) != std::string::npos) matched.push_back(entry);
    }
    if (matched.size() != 1) return std::nullopt;
    return matched.front();
}

nlohmann::json cancelMatchingEvent(DSLEngine& engine, const std::string& match) {
    auto found = findSingleEvent(engine, match);
    if (!found) return {{"match", match}, {"cancelled", false}, {"error", "did not match exactly one event"}};
    return {
        {"match", match},
        {"kind", found->value("kind", std::string())},
        {"status_before", found->value("status", std::string())},
        {"cancelled", engine.cancelEvent(found->at("id").get<unsigned long>())},
    };
}

nlohmann::json replaceMatchingEvent(DSLEngine& engine, const std::string& match, const std::string& new_text) {
    auto found = findSingleEvent(engine, match);
    if (!found) return {{"match", match}, {"replaced", false}, {"error", "did not match exactly one event"}};
    try {
        engine.replaceEventIfReady(found->at("id").get<unsigned long>(), new_text, "dsl_test");
        return {{"match", match}, {"replaced", true}, {"kind", found->value("kind", std::string())}};
    } catch (const std::exception& e) {
        return {{"match", match}, {"replaced", false}, {"error", e.what()}};
    }
}

nlohmann::json readJson(const std::filesystem::path& path) {
    std::ifstream stream(path);
    return nlohmann::json::parse(stream);
}

int main(int argc, char** argv) {
    std::vector<std::string> args(argv + 1, argv + argc);
    bool update = std::find(args.begin(), args.end(), "--update") != args.end();
    std::erase(args, "--update");
    if (args.size() != 1) {
        std::cerr << "usage: dsl_test <case directory> [--update]\n";
        return 2;
    }
    std::filesystem::path case_dir = args.front();

    spdlog::set_level(spdlog::level::trace);  // Only printed for failing tests, so allowed to be verbose

    CaseSpec spec = readCaseSpec(case_dir);

    // Build a mock of the usual config.toml, use a very high speedup instead of running the cases in real-time for responsiveness of the tests
    std::string config_text = "[master]\nperiod = " + std::to_string(spec.period) + "\nspeedup = 1e9\n";
    if (spec.reload_at) {
        // The Orchestrator emits its DumpStateEvent every dump_period, so one dump event lands at reload_at
        config_text += "dump_period = " + std::to_string(*spec.reload_at) + "\n";
    }
    config_text += "[input_files]\ndsl_file = \"script.dsl\"\n";
    toml::table config = toml::parse(config_text);

    Orchestrator::create(case_dir, config, 0.0, spec.duration, "dsl_test");

    ExampleDynawoInterface dynawo_interface(NORDIC_NETWORK_FILE, NORDIC_OUTPUTS_FILE, NORDIC_INPUTS_FILE);

    RecordingScenarioHandler scenario_handler;
    scenario_handler.setNetwork(
        {"CC", "SCADA", "substation_1", "substation_2"},
        {{"substation_1", {"CC"}}, {"substation_2", {"CC"}}, {"CC", {"SCADA", "substation_1", "substation_2"}}});
    scenario_handler.failValidationWhen([&dynawo_interface](const nlohmann::json& scenario) -> std::string {
        // Mock of the ScenarioHandler validation step, fails for the commands whose input the dynawo interface does not have
        std::string command = scenario.value("command", std::string());
        std::string attribute = scenario.value("attribute", std::string());
        if (command == "iidm_command" || command == "scale_multiplier") {
            std::string iidm_id = scenario.value("iidm_id", std::string());
            if (!dynawo_interface.hasInput(iidm_id, attribute)) {
                return "No game master input with iidm " + iidm_id + " and attribute " + attribute;
            }
        } else if (command == "dynamic_model_command" || command == "dynamic_model_scale_multiplier") {
            std::string dynamic_model = scenario.value("dynamic_model", std::string());
            try {
                dynawo_interface.getInputFromDynamicModel(dynamic_model, attribute);
            } catch (const std::exception& e) {
                return e.what();
            }
        }
        return "OK";
    });
    TmpDirClickHouseLogger logger("dsl_test_" + case_dir.filename().string());

    // Only the measurements inside a phase's window, so a reload's second half does not replay the first's
    auto schedule_measurements = [&](double from, double to) {
        for (auto& measurement : spec.measurements) {
            if (measurement.time < from || measurement.time >= to) continue;
            Orchestrator::get().emitLater(
                ActualMeasurement(measurement.dynamic_model.empty()
                                      ? dynawo_interface.getOutputFromIidm(measurement.iidm_id, measurement.attribute)
                                      : dynawo_interface.getOutputFromDynamicModel(measurement.dynamic_model, measurement.attribute),
                                   Value(measurement.value), measurement.time, "dsl_test"),
                measurement.time);
        }
    };

    nlohmann::json result;
    bool loaded = false;
    {
        // Scoped so the engine is destroyed, and its replay log archived, before any reload below
        std::optional<DSLEngine> engine;
        try {
            engine.emplace(true, scenario_handler, dynawo_interface, logger, 0.0);
            loaded = true;
        } catch (const std::exception& e) {
            // A case can assert on a rejection just as well as on a run
            result["load_error"] = e.what();
        }

        if (engine) {
            for (auto& partial : spec.completions) {
                auto completions = engine->complete(partial);
                result["completions"][partial] = {{"suggestions", completions.suggestions},
                                                 {"replace_from", completions.replace_from}};
            }
            schedule_measurements(0.0, spec.reload_at.value_or(spec.duration));
            if (spec.cancel_at) {
                Orchestrator::get().run(spec.cancel_at);  // Leaves the queue intact, so the run below resumes it
                result["cancellation"] = cancelMatchingEvent(*engine, spec.cancel_match);
            }
            if (spec.command_at) {
                Orchestrator::get().run(spec.command_at);
                try {
                    engine->loadScript(spec.command, "dsl_terminal");
                } catch (const std::exception& e) {
                    result["command_error"] = e.what();
                }
            }
            if (spec.replace_at) {
                Orchestrator::get().run(spec.replace_at);
                result["replacement"] = replaceMatchingEvent(*engine, spec.replace_match, spec.replace_with);
            }
            Orchestrator::get().run(spec.reload_at);
        }
    }

    if (loaded && spec.reload_at) {
        // Create a fresh Orchestrator (with empty event queue as in a real dump/reload cycle) and reload the DSLEngine from dump
        result["reloaded_at"] = *spec.reload_at;
        Orchestrator::create(case_dir, config, *spec.reload_at, spec.duration, "dsl_test");
        try {
            DSLEngine reloaded(scenario_handler, dynawo_interface, logger, *spec.reload_at);
            schedule_measurements(*spec.reload_at, spec.duration);
            Orchestrator::get().run(std::nullopt);
        } catch (const std::exception& e) {
            result["reload_error"] = e.what();
        }
    }
    result["applied"] = scenario_handler.applied();

    auto expected_path = case_dir / "expected.json";
    if (update) {
        std::ofstream(expected_path) << result.dump(2) << "\n";
        std::cout << "updated " << expected_path.string() << "\n";
        return 0;
    }
    if (!std::filesystem::exists(expected_path)) {
        std::cerr << "no golden file at " << expected_path.string() << "; run this case with --update to create it\n";
        return 1;
    }
    if (readJson(expected_path) == result) return 0;

    logger.keep();  // Keep the logger artefacts on failed runs for debug purposes
    std::cerr << case_dir.filename().string() << ": the engine did not do what the golden file says.\n"
              << "--- expected ---\n" << readJson(expected_path).dump(2)
              << "\n--- actual ---\n" << result.dump(2)
              << "\nartefacts kept in " << logger.directory().string() << "\n";
    return 1;
}
