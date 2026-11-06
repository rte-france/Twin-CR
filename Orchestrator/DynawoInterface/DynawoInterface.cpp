/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DynawoInterface.h"
#include "DynawoHandlers/XmlHandler.h"
#include "Information.h"
#include "Orchestrator.h"
#include "ProcessLauncher.h"
#include "SignalHandler.h"
#include "../utils/JsonExtension.h"
#include "../utils/TomlExtension.h"
#include "Tase2.h"

#include <cstdint>
#include <mimalloc.h>
#include <nlohmann/json_fwd.hpp>
#include <nlohmann/json.hpp>
#include <optional>
#include <spdlog/spdlog.h>
#include <stdexcept>
#include <thread>

#include <csignal>
#include <fstream>
#include <memory>
#include <random>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#if not defined(_WIN32)
#include <unistd.h>
#endif

// Ids/topics/destinations end up in fixed-size char[128] fields of the Broker's ring buffer (RingBuffer.h).
// Reject them here, at config load, instead of during the simulation
constexpr size_t MAX_RING_BUFFER_FIELD_LENGTH = 128;

inline void checkStringLength(const std::string& value, const std::string& field_name) {
    if (value.size() >= MAX_RING_BUFFER_FIELD_LENGTH) {
        throw std::invalid_argument(
            field_name + " '" + value + "' is " + std::to_string(value.size()) +
            " characters long, exceeding the " + std::to_string(MAX_RING_BUFFER_FIELD_LENGTH - 1) + "-character limit"
        );
    }
}

inline std::string alphabeticSideToNumeric(const std::string& side) {
    if (side == "ONE") {
        return "1";
    } else if (side == "TWO") {
        return "2";
    } else if (side == "THREE") {
        return "3";
    } else {
        throw std::invalid_argument("Unknown side: " + side);
    }
}

// Simple deterministic hash function
inline uint64_t fnl_hash(std::string_view str) {
    // Remove the "_value" suffix before computing the hash as this suffix tends to be added/removed in between Dynawo versions
    constexpr std::string_view suffix = "_value";
    if (str.ends_with(suffix))
        str.remove_suffix(suffix.size());

    // Compute hash of s
    uint64_t seed = 14695981039346656037ULL;
    for (unsigned char c : str) {
        seed ^= c;
        seed *= 1099511628211ULL;
    }
    return seed;
}

DynawoInterface::DynawoInterface(const InformationFlowModel& information_flow_model, double dynawo_start_time, double actual_start_time, double end_time, ClickHouseLogger& logger, ProcessLauncher& process_launcher, bool save_input_files):
end_time_(end_time),
dynawo_running_(false),
sender_(DynawoSender(5555)),
curve_receiver_(DynawoReceiver(5556, "curves_values")),
curve_names_receiver_(DynawoReceiver(5556, "curves_names")),
timeline_receiver_(DynawoReceiver(5556, "timeline")),
constraints_receiver_(DynawoReceiver(5556, "constraints")),
logger_(logger),
subprocess_(process_launcher) {
    const auto& working_dir = Orchestrator::get().getWorkingDir();
    const auto& config = Orchestrator::get().getConfig();

    my_env_dynawo_path_ = working_dir / get_or_throw<std::string>(config, {"master", "myEnvDynawo_path"});
    if (!std::filesystem::exists(my_env_dynawo_path_)) {
        throw std::invalid_argument(std::string("Dynawo executable path (") + my_env_dynawo_path_.c_str() + ") not found");
    }
    std::filesystem::path dyd_file = working_dir / get_or_throw<std::string>(config, {"input_files", "dyd_file"});
    game_master_inputs_file_ = working_dir / get_or_throw<std::string>(config, {"input_files", "game_master_inputs_file"});
    game_master_outputs_file_ = working_dir / get_or_throw<std::string>(config, {"input_files", "game_master_outputs_file"});
    std::filesystem::path scada_outputs_file = working_dir / get_or_throw<std::string>(config, {"input_files", "scada_outputs_file"});
    job_file_ = working_dir / get_or_throw<std::string>(config, {"input_files", "job_file"});
    period_ = get_or_throw<double>(config, {"master", "period"});

    DydHandler dyd_handler = DydHandler(dyd_file);
    dynawo_events_ = dyd_handler.getEvents();

    JobHandler job_handler = JobHandler(job_file_);
    has_timeline_ = job_handler.hasTimeline();
    has_constraints_ = job_handler.hasConstraints();
    iidm_handler_ = std::make_unique<IIDMHandler>(job_handler.getIidm());

    auto game_master_inputs = nlohmann::json::parse(std::ifstream(game_master_inputs_file_));
    std::unordered_map<std::string, ModelParameters*> model_parameters_by_name;
    for (auto dynawo_input : game_master_inputs) {
        try {
            std::string simulator = dynawo_input["simulator"];
            if (simulator != "dynawo") {
                continue;
            }
            std::string id = dynawo_input["id"];
            checkStringLength(id, "Dynawo game master input id");
            double factor = get_or_default(dynawo_input, {"factor"}, 1.0);
            std::string attribute = dynawo_input["kind"];
            if (dynawo_input.contains("side")) {
                std::string side = dynawo_input["side"];
                attribute += alphabeticSideToNumeric(side);
            }

            if (dynawo_input.contains("equipmentId") && dynawo_input["equipmentId"].is_string()) {
                std::string iidm_id = dynawo_input["equipmentId"];
                iidm_to_dynawo_input_[IIDM_key(iidm_id, attribute)] = id;
            } else if (dynawo_input.contains("model") && dynawo_input.contains("model_lib")) {
                // Purely dynamic model
                std::string dynamic_model = dynawo_input["model"];
                dynamic_model_to_dynawo_input_[DynamicModel_key(dynamic_model, attribute)] = id;
                model_lib_by_dynamic_model_[dynamic_model] = dynawo_input["model_lib"];
            } else {
                throw std::invalid_argument("Dynawo game master input " + id + " is neither IIDM equipment (equipmentId) nor a dynamic model (model and model_lib), check "
                                            + game_master_inputs_file_.string());
            }

            dynawo_input_by_id_.emplace(id, DynawoInput(id, factor));

            // Load the parameter events (not included in the dyd_file)
            if (!dynawo_events_.contains(id) && dynawo_input.contains("model") && dynawo_input.contains("variable")) {
                std::string model_name = dynawo_input["model"];
                std::string variable_name = dynawo_input["variable"];
                if (!model_parameters_by_name.contains(model_name)) {
                    auto model_param = std::make_unique<ModelParameters>(model_name);
                    model_parameters_by_name[model_name] = model_param.get();
                    dynawo_events_[model_name] = std::move(model_param);
                }
                model_parameters_by_name[model_name]->addParameter(variable_name);
                model_parameters_ids_[id] = {model_parameters_by_name[model_name], variable_name};
				spdlog::debug("Adding model parameter {}.{} to Dynawo -> {}", model_name, variable_name, id);
            }
        } catch (const nlohmann::detail::type_error& e) {
            throw std::invalid_argument("Invalid Dynawo game master input: " + std::string(e.what()) + " in:\n" + dynawo_input.dump());
        }
    }

    auto game_master_outputs = nlohmann::json::parse(std::ifstream(game_master_outputs_file_));
    for (auto dynawo_output : game_master_outputs) {
        try {
            std::string simulator = dynawo_output["simulator"];
            if (simulator != "dynawo") {
                continue;
            }
            std::string id = dynawo_output["id"];
            checkStringLength(id, "Dynawo game master output id");
            std::string curve_name = dynawo_output["dynawo_id"];
            std::string topic  = dynawo_output["topic"];
            checkStringLength(topic, "Dynawo game master output topic");
            double factor = get_or_default(dynawo_output, {"factor"}, 1.0);
            std::string attribute = dynawo_output["kind"];
            if (dynawo_output.contains("side")) {
                std::string side = dynawo_output["side"];
                attribute += alphabeticSideToNumeric(side);
            }

            if (dynawo_output.contains("equipmentId") && dynawo_output["equipmentId"].is_string()) {
                std::string iidm_id = dynawo_output["equipmentId"];
                iidm_to_dynawo_output_[IIDM_key(iidm_id, attribute)] = id;
            } else if (dynawo_output.contains("model") && dynawo_output.contains("model_lib")) {
                // Purely dynamic model: keyed on its own name, since it has no equipment to be keyed on
                std::string dynamic_model = dynawo_output["model"];
                dynamic_model_to_dynawo_output_[DynamicModel_key(dynamic_model, attribute)] = id;
                model_lib_by_dynamic_model_[dynamic_model] = dynawo_output["model_lib"];
            } else {
                throw std::invalid_argument("Dynawo game master output " + id + " is neither IIDM equipment (equipmentId) nor a dynamic model (model and model_lib), check "
                                            + game_master_outputs_file_.string());
            }

            auto game_master_output = GameMaster_output(id, topic, factor);
            game_master_outputs_by_curve_name_[curve_name].push_back(game_master_output);
        } catch (const nlohmann::detail::type_error& e) {
            throw std::invalid_argument("Invalid Dynawo game master output: " + std::string(e.what()) + " in:\n" + dynawo_output.dump());
        }
    }

    auto scada_outputs = nlohmann::json::parse(std::ifstream(scada_outputs_file));
    for (auto dynawo_output : scada_outputs) {
        try {
            std::string simulator = dynawo_output["simulator"];
            if (simulator != "dynawo") {
                continue;
            }
            std::string id = dynawo_output["id"];
            checkStringLength(id, "Dynawo scada output id");
            std::string curve_name = dynawo_output["dynawo_id"];
            std::string source = dynawo_output["source"];
            std::string destination = dynawo_output["destination"];
            checkStringLength(destination, "Dynawo scada output destination");
            auto routing = information_flow_model.getPath(source, destination);
            std::string topic = dynawo_output["topic"];
            checkStringLength(topic, "Dynawo scada output topic");
            auto tase2_id = get_optional<std::string>(dynawo_output, {"tase2"});
            if (tase2_id.has_value()) {
                checkStringLength(*tase2_id, "Dynawo scada output tase2 id");
            }
            double factor = get_or_default(dynawo_output, {"factor"}, 1.0);
            bool publish_on_change = get_or_default(dynawo_output, {"publish_on_change"}, false);
            double last_value = get_or_default(dynawo_output, {"last_value"}, -999);
            double period = get_or_default(dynawo_output, {"period"}, 0);
            double period_offset;
            if (dynawo_output.contains("period_offset")) {
                period_offset = dynawo_output["period_offset"];
            } else {
                std::uniform_real_distribution<> distrib(0, period);
                std::mt19937 rng(fnl_hash(id));
                period_offset = distrib(rng);
            }

            auto scada_output = std::make_shared<SCADA_output>(id, destination, routing, topic, tase2_id,
                factor, publish_on_change, last_value, period, period_offset, dynawo_start_time);
            scada_outputs_by_curve_name_[curve_name].push_back(scada_output);
            scada_outputs_by_scada_id_[id].push_back(scada_output);
        } catch (const nlohmann::detail::type_error& e) {
            throw std::invalid_argument("Invalid Dynawo scada output: " + std::string(e.what()) + " in:\n" + dynawo_output.dump());
        }
    }

    start_time_ = actual_start_time;
    step_index_ = 1;
    next_dynawo_time_ = start_time_ + step_index_ * period_;  // Not next_time += period to avoid accumulating drift

    Orchestrator::get().subscribeTo<ControlReceived, &DynawoInterface::onControlReceived>(this);
    Orchestrator::get().subscribeTo<ActualControl, &DynawoInterface::onActualControl>(this);

    // Starts Dynawo at t=0 (i.e. when the orchestrator starts (after all modules are initialized))
    Orchestrator::get().scheduleEvent(
        dynawo_start_time,
        makeCallback<&DynawoInterface::initDynawo>(this, dynawo_start_time, actual_start_time)
    );

    // Workaround json not releasing memory (https://github.com/nlohmann/json/issues/1924)
    game_master_outputs.clear();
    scada_outputs.clear();
    mi_collect(true);

    if (save_input_files)
        logInputFiles();
}

void DynawoInterface::applyControl(const std::string& id, const Value& value) {
    double factor;
    if (!dynawo_input_by_id_.contains(id)) {
        spdlog::warn("{} not in Dynawo inputs, skipping (but might actually not be intended for Dynawo)", id);
        return;
    }
    factor = dynawo_input_by_id_.at(id).factor;
    Value scaled_value = value;
    scaled_value.update(value.to_double() / factor);

    if (model_parameters_ids_.contains(id)) {
        auto [model_param, variable_name] = model_parameters_ids_.at(id);
        spdlog::debug("Sending value {} (scaled to {}) for id {} (model {}, variable {})", value, scaled_value, id, model_param->name(), variable_name);
        // update a parameter value and send the parameters already set for the model (never set ones keep their par file value).
        //  If multiple parameters are changed for the same model at one time step, the last action sent should
        //  bear all the updated values (Dynawo consider only the last action, previous actions are overwritten).
        //  e.g. modifying P/Q for Model:
        //    - launchEvent updating P, -> Model,P,newP
        //    - launchEvent updating Q, -> Model,P,newP,Q,newQ
        model_param->launchEvent(variable_name, scaled_value.value, sender_);
    } else if (dynawo_events_.contains(id)) {
        spdlog::debug("Sending value {} (scaled to {}) for id {}", value, scaled_value, id);
        dynawo_events_.at(id)->launchEvent(scaled_value.value, sender_);
    } else {
        spdlog::warn("{} not in Dynawo events, skipping (but might actually not be intended for Dynawo)", id);
        return;
    }

    // Reset the event after use so that it can be reused if needed (need to wait at least one Dynawo time step before it can actually be reused)
    Orchestrator::get().scheduleEvent(
        current_time_ + (2 * period_),
        makeCallback<&DynawoInterface::resetControl>(this, id)
    );
}

void DynawoInterface::scaleMultiplierBy(const std::string& id, double multiplier_increase) {
    if (!dynawo_events_.contains(id)) {
        spdlog::warn("{} not in Dynawo events, skipping scaleMultiplierBy", id);
        return;
    }
    auto* event = dynawo_events_.at(id).get();
    if (auto* discrete = dynamic_cast<UpdatableDiscrete*>(event)) {
        discrete->scaleMultiplierBy(multiplier_increase, sender_);
    } else if (auto* continuous = dynamic_cast<UpdatableContinuous*>(event)) {
        continuous->scaleMultiplierBy(multiplier_increase, sender_);
    } else {
        spdlog::warn("{} is not an UpdatableDiscrete/UpdatableContinuous, skipping scaleMultiplierBy", id);
    }
}

void DynawoInterface::resetControl(const std::string& control_id) {
    if (dynawo_events_.contains(control_id))
        dynawo_events_.at(control_id)->reset(sender_);
}

void DynawoInterface::onControlReceived(const ControlReceived& info) {
    applyControl(info.id, info.value);
}

void DynawoInterface::onActualControl(const ActualControl& info) {
    applyControl(info.id, info.value);
}

void DynawoInterface::getDynawoCurveNames() {
    std::string message = curve_names_receiver_.receive_string();
    std::istringstream f(message);
    std::string curve_name;

    // Curves are always sent in the same order, so we store all needed info
    // to generate game master and SCADA outputs in vectors to avoid map operations.

    if (SignalHandler::gotExitSignal()) {
        return;
    }

    // First line is "time", not a real curve
    if (!std::getline(f, curve_name)) {
        throw std::runtime_error("Illformed Dynawo message: " + message);
    }

    // Remaining lines are actual curve names
    while (std::getline(f, curve_name)) {
        // Data needed to generate measurement for the Game Master
        if (game_master_outputs_by_curve_name_.contains(curve_name)) {
            for (auto& game_master_output : game_master_outputs_by_curve_name_.at(curve_name)) {
                game_master_outputs_by_curve_index_.push_back(game_master_output);
            }
            game_master_outputs_per_curve_.push_back(game_master_outputs_by_curve_name_.at(curve_name).size());
        } else {
            game_master_outputs_per_curve_.push_back(0);
        }

        // Data needed to generate measurement for the SCADA
        if (scada_outputs_by_curve_name_.contains(curve_name)) {
            for (auto& scada_output : scada_outputs_by_curve_name_.at(curve_name)) {
                scada_outputs_by_curve_index_.push_back(scada_output);
            }
            scada_outputs_per_curve_.push_back(scada_outputs_by_curve_name_.at(curve_name).size());
        } else {
            scada_outputs_per_curve_.push_back(0);
        }
    }
    // Delete maps which are no longer useful
    game_master_outputs_by_curve_name_.clear();
    scada_outputs_by_curve_name_.clear();
    // Workaround mimalloc not releasing memory (https://github.com/nlohmann/json/issues/1924)
    mi_collect(true);
}

void DynawoInterface::goToNextTimeStep() {
    // Tell Dynawo to go to the next time step
    std::string reply = sender_.goToNextTimeStep();
    if (reply == "stop") {
        return;
    }

    // Read measurements and send them to the Game Master and/or SCADA
    std::vector<double> values = curve_receiver_.receive_bytes();

    if (values.empty()) {
        if (SignalHandler::gotExitSignal()) {
            return;
        }
        throw std::runtime_error("Illformed Dynawo message");
    }
    // First value is time
    double time = values.front();
    current_time_ = time;

    int i = 0;
    int game_master_i = 0;
    int scada_i = 0;
    // Remaining values are curve values
    for (auto it = values.begin() + 1; it != values.end(); it++) {
        double value = *it;

        // Generate measurement for the Game Master
        for (int _ = 0; _ < game_master_outputs_per_curve_[i]; _++) {
            GameMaster_output& game_master_output = game_master_outputs_by_curve_index_[game_master_i];
            Orchestrator::get().emit(ActualMeasurement(game_master_output.id, value * game_master_output.factor, current_time_, game_master_output.topic));
            game_master_i++;
        }

        // Generate measurement for the SCADA
        for (int _ = 0; _ < scada_outputs_per_curve_[i]; _++) {
            auto& scada_output = *scada_outputs_by_curve_index_[scada_i];
            bool do_emit = true;
            double local_value = value * scada_output.factor;
            if (scada_output.publish_on_change) {
                if (scada_output.last_value != local_value) {
                    scada_output.last_value = local_value;
                } else {
                    do_emit = false;
                }
            }
            if (scada_output.period != 0) {
                if (current_time_ >= scada_output.last_publication_time + scada_output.period) {
                    scada_output.last_publication_time += scada_output.period;
                } else {
                    do_emit = false;
                }
            }

            if (scada_output.requested) {
                scada_output.requested = false;
                do_emit = true;  // Force emission if requested
            }

            std::optional<tase2::Tase2Extension> tase2_extension;
            if (scada_output.tase2_id.has_value()) {
                tase2::SignalisationType signalisation_type;
                int cause;
                if (scada_output.publish_on_change) {
                    cause = tase2::CAUSE_SPONTANEOUS;
                    signalisation_type = tase2::SignalisationType::TS;
                } else {
                    cause = tase2::CAUSE_PERIODIC;
                    signalisation_type = tase2::SignalisationType::TM;
                }
                int validity = tase2::QUALITY_VALIDITY_GOOD;
                bool operator_blocked = false;

                tase2_extension.emplace(scada_output.tase2_id.value(), signalisation_type, cause, validity, operator_blocked);
            }

            if (do_emit) {
                Orchestrator::get().emit(MeasurementSent(scada_output.id, local_value, current_time_,
                    scada_output.destination, scada_output.routing, scada_output.topic, tase2_extension));
            }
            scada_i++;
        }
        i++;
    }

    if (has_timeline_) {
        std::string timeline = timeline_receiver_.receive_string();
        if (timeline == "stop") return;
        auto json_timeline = nlohmann::json::parse(timeline);
        if (json_timeline.is_array()) {
            for (const auto& timeline_event : json_timeline) {
                Orchestrator::get().emit(DynawoTimelineEvent(timeline_event.dump()));
            }
        }
    }

    if (has_constraints_) {
        std::string constraints = constraints_receiver_.receive_string();
        if (constraints == "stop") return;
        auto json_constraint = nlohmann::json::parse(constraints);
        if (json_constraint.is_array()) {
            for (const auto& constraint_event : json_constraint) {
                Orchestrator::get().emit(DynawoConstraintEvent(constraint_event.dump()));
            }
        }
    }

    // Schedule next time step
    step_index_++;
    next_dynawo_time_ = start_time_ + step_index_ * period_;  // Not next_time += period to avoid accumulating drift
    if (next_dynawo_time_ < end_time_) {
        Orchestrator::get().scheduleEvent(
            next_dynawo_time_,
            makeCallback<&DynawoInterface::goToNextTimeStep>(this),
            Event::Order::DynawoStep
        );
    }
}

void DynawoInterface::requestSCADAPublication(std::vector<std::string> scada_ids) {
    for (const auto& id : scada_ids) {
        if (scada_outputs_by_scada_id_.contains(id)) {
            for (auto& scada_output : scada_outputs_by_scada_id_.at(id)) {
                scada_output->requested = true;
            }
        } else {
            spdlog::warn("{} not in Dynawo scada outputs", id);
        }
    }
}

std::string DynawoInterface::getInputFromIidm(const std::string& iidm_id, const std::string& attribute) const {
    IIDM_key key(iidm_id, attribute);
    if (iidm_to_dynawo_input_.contains(key)) {
        return iidm_to_dynawo_input_.at(key);
    } else {
        throw std::invalid_argument("No game master input with iidm " + iidm_id + " and attribute " + attribute + ", please update " + game_master_inputs_file_.string());
    }
}

static std::vector<std::string> attributesOf(const std::unordered_map<IIDM_key, std::string, IIDM_key_hash>& mapping,
                                              const std::string& iidm_id) {
    std::vector<std::string> attributes;
    for (auto& [key, dynawo_id] : mapping) {
        if (key.iidm_id == iidm_id) attributes.push_back(key.attribute);
    }
    return attributes;
}

std::vector<std::string> DynawoInterface::listInputAttributes(const std::string& iidm_id) const {
    return attributesOf(iidm_to_dynawo_input_, iidm_id);
}

std::vector<std::string> DynawoInterface::listOutputAttributes(const std::string& iidm_id) const {
    return attributesOf(iidm_to_dynawo_output_, iidm_id);
}

std::string DynawoInterface::getOutputFromIidm(const std::string& iidm_id, const std::string& attribute) const {
    IIDM_key key(iidm_id, attribute);
    if (iidm_to_dynawo_output_.contains(key)) {
        return iidm_to_dynawo_output_.at(key);
    } else {
        throw std::invalid_argument("No game master output with iidm " + iidm_id + " and attribute " + attribute + ", check " + game_master_outputs_file_.string());
    }
}

std::vector<std::string> DynawoInterface::listIidmIds(const std::string& pypowsybl_type) const {
    return iidm_handler_->getIds(pypowsybl_type);
}

std::string DynawoInterface::getInputFromDynamicModel(const std::string& dynamic_model, const std::string& kind) const {
    DynamicModel_key key(dynamic_model, kind);
    if (dynamic_model_to_dynawo_input_.contains(key)) {
        return dynamic_model_to_dynawo_input_.at(key);
    } else {
        throw std::invalid_argument("No game master input with model " + dynamic_model + " and kind " + kind + ", check " + game_master_inputs_file_.string());
    }
}

std::vector<std::string> DynawoInterface::listDynamicModelLibs(DynamicModelDirection direction) const {
    // Only return a lib if it has an input (or output depending on direction)
    auto& mapping = direction == DynamicModelDirection::Input ? dynamic_model_to_dynawo_input_ : dynamic_model_to_dynawo_output_;
    std::set<std::string> libs;
    for (auto& [key, dynawo_id] : mapping) {
        if (model_lib_by_dynamic_model_.contains(key.dynamic_model)) {
            libs.insert(model_lib_by_dynamic_model_.at(key.dynamic_model));
        }
    }
    return {libs.begin(), libs.end()};
}

std::vector<std::string> DynawoInterface::listDynamicModelIds(const std::string& model_lib, DynamicModelDirection direction) const {
    auto& mapping = direction == DynamicModelDirection::Input ? dynamic_model_to_dynawo_input_ : dynamic_model_to_dynawo_output_;
    std::set<std::string> dynamic_models;
    for (auto& [key, dynawo_id] : mapping) {
        if (model_lib_by_dynamic_model_.contains(key.dynamic_model)
            && model_lib_by_dynamic_model_.at(key.dynamic_model) == model_lib) {
            dynamic_models.insert(key.dynamic_model);
        }
    }
    return {dynamic_models.begin(), dynamic_models.end()};
}

std::string DynawoInterface::getOutputFromDynamicModel(const std::string& dynamic_model, const std::string& kind) const {
    DynamicModel_key key(dynamic_model, kind);
    if (dynamic_model_to_dynawo_output_.contains(key)) {
        return dynamic_model_to_dynawo_output_.at(key);
    } else {
        throw std::invalid_argument("No game master output with model " + dynamic_model + " and kind " + kind + ", check " + game_master_outputs_file_.string());
    }
}

/** The kinds one dynamic model offers in the given direction. */
static std::vector<std::string> kindsOf(const std::unordered_map<DynamicModel_key, std::string, DynamicModel_key_hash>& mapping,
                                         const std::string& dynamic_model) {
    std::vector<std::string> kinds;
    for (auto& [key, dynawo_id] : mapping) {
        if (key.dynamic_model == dynamic_model) kinds.push_back(key.kind);
    }
    return kinds;
}

std::vector<std::string> DynawoInterface::listDynamicModelInputKinds(const std::string& dynamic_model) const {
    return kindsOf(dynamic_model_to_dynawo_input_, dynamic_model);
}

std::vector<std::string> DynawoInterface::listDynamicModelOutputKinds(const std::string& dynamic_model) const {
    return kindsOf(dynamic_model_to_dynawo_output_, dynamic_model);
}

DynawoInterface::~DynawoInterface() {
    if (dynawo_running_) {
        if (!SignalHandler::gotExitSignal()) {
            sender_.stopDynawo();
        } else {
            // ZMQ handler possibly not able to send stop request anymore, so kill Dynawo instead
            subprocess_.kill();
        }
    }
    if (std_out_reader_.joinable()) {  // If it as actually been started
        std_out_reader_.join();
    }
}

void DynawoInterface::logInputFiles() {
    auto input_files = JobHandler(job_file_).getAllInputPaths();
    for (auto& input_file : input_files) {
        logger_.logInputFile(input_file);
    }
}

void DynawoInterface::logOutputFiles() {
    JobHandler job_handler = JobHandler(job_file_);

    auto log_paths = job_handler.getLogPaths();
    auto output_iidm_path = job_handler.getOutputIidmPath();
    auto fsv_path = job_handler.getOutputFinalStateValuesPath();

    for (auto& log_path : log_paths) {
        logger_.logOutputFile(log_path);
    }
    if (output_iidm_path.has_value()) {
        logger_.logOutputFile((*output_iidm_path));
    }
    if (fsv_path.has_value()) {
        logger_.logOutputFile((*fsv_path));
    }
}

void DynawoInterface::initDynawo(double dynawo_start_time, double actual_start_time) {
    std::string command = my_env_dynawo_path_.generic_string() + " jobs -i " + job_file_.generic_string();
    subprocess_.start(command);
    dynawo_running_ = true;

    std_out_reader_ = std::thread([this]() {
        char buffer[4096];
        auto log_level = spdlog::level::trace;
        while (true) {
            int rc = subprocess_.read_output(buffer, sizeof(buffer) - 1);

            if (rc == 0) {
                break; // EOF
            }

            buffer[rc] = '\0';  // null terminate
            std::istringstream chunk(buffer);
            std::string line;
            while (std::getline(chunk, line)) {
                if (line.find("Error") != std::string::npos || line.find("Exception") != std::string::npos) {
                    log_level = spdlog::level::critical;  // Raise log level to critical if a Dynawo error occurs
                }
                spdlog::log(log_level, "Dynawo Output: {}", line);
            }
        }

        dynawo_running_ = false;
        if (current_time_ < end_time_ - period_) {
            spdlog::error("DynawoInterface: Process ended unexpectedly! current_time={}, end_time={}", current_time_.load(), end_time_);
            // Dynawo process ended unexpectedly ==> Raise signal to stop simulation
            SignalHandler::interrupt();
        }  // Else, normal Dynawo exit ==> Nothing to do

    });

    getDynawoCurveNames();

    double current_time = dynawo_start_time;
    while (current_time < actual_start_time) {
        spdlog::info("Running Dynawo loop from {} to start time {}, this emulates Dynawo's future dump/load capability", current_time, actual_start_time);
        std::string reply = sender_.goToNextTimeStep();
        if (reply == "stop") {
            return;
        }

        // Read measurements, but don't actually publish them (emulates start from dump)
        std::vector<double> values = curve_receiver_.receive_bytes();
        if (has_timeline_) std::string timeline = timeline_receiver_.receive_string();
        if (has_constraints_) std::string constraints = constraints_receiver_.receive_string();

        if (values.empty()) {
            if (SignalHandler::gotExitSignal()) {
                return;
            }
            throw std::runtime_error("Illformed Dynawo message");
        }
        current_time += period_;
    }

    Orchestrator::get().scheduleEvent(
        next_dynawo_time_,
        makeCallback<&DynawoInterface::goToNextTimeStep>(this),
        Event::Order::DynawoStep
    );
}
