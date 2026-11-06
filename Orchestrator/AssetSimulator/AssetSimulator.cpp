/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "AssetSimulator.h"
#include "AssetModels/SubstationAlarm.h"
#include "AssetModels/Recloser.h"
#include "AssetModels/OverloadAlarm.h"
#include "Information.h"
#include "InformationFlowModel.h"
#include "Orchestrator.h"
#include "ValueHolder.h"

#include <mimalloc.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <memory>
#include <optional>
#include <vector>


enum class AssetModels {
    OverloadAlarm,
    SubstationAlarm,
    Recloser,
    ValueHolder
};

[[maybe_unused]] static AssetModels stringToAssetModel(const std::string& str) {
    if (str == "OverloadAlarm")  return AssetModels::OverloadAlarm;
    if (str == "SubstationAlarm") return AssetModels::SubstationAlarm;
    if (str == "Recloser")  return AssetModels::Recloser;
    if (str == "ValueHolder")  return AssetModels::ValueHolder;
    throw std::runtime_error("Unknown asset model type " + str);
}

AssetSimulator::AssetSimulator(const InformationFlowModel& information_flow_model, ClickHouseLogger& logger) :
logger_(logger) {
    const auto& working_dir = Orchestrator::get().getWorkingDir();
    const auto& config = Orchestrator::get().getConfig();

    std::optional<std::string> relative_path = config["input_files"]["asset_simulator_config_file"].value<std::string>();
    if (!relative_path.has_value()) {
        spdlog::warn("No config file specified for the asset simulator. The asset simulator will not be used.");
        return;
    }
    nlohmann::json j;
    try {
        j = nlohmann::json::parse(std::ifstream(working_dir / *relative_path));
    } catch (const nlohmann::json::parse_error& e) {
        throw std::invalid_argument("Failed to parse JSON file '" + (working_dir / *relative_path).string() + "': " + e.what());
    }
    buildAssetModels(j, information_flow_model);

    initSubscriptions();

    // Workaround json not releasing memory (https://github.com/nlohmann/json/issues/1924)
    j.clear();
    mi_collect(true);
}

AssetSimulator::AssetSimulator(ClickHouseLogger& logger, double time) :
logger_(logger) {
    auto& config = Orchestrator::get().getConfig();

    std::optional<std::string> relative_path = config["input_files"]["asset_simulator_config_file"].value<std::string>();
    if (!relative_path.has_value()) {
        spdlog::warn("No config file specified for the asset simulator. The asset simulator will not be used.");
        return;
    }

    std::string string_buf = logger_.loadDump("AssetSimulator", time);

    std::istringstream ss(string_buf);
    ser20::BinaryInputArchive ar(ss);

    ar(*this);

    initSubscriptions();
}

void AssetSimulator::initSubscriptions() {
    // Measurement/control received are forwarded to assets that subscribe to the id of the info, and match its destination
    Orchestrator::get().subscribeTo<MeasurementReceived, &AssetSimulator::onMeasurementReceived>(this);
    Orchestrator::get().subscribeTo<ControlReceived, &AssetSimulator::onControlReceived>(this);
    // Actual Measurement/controls are forwarded to assets that subscribe to the id of the info, and match its destination
    Orchestrator::get().subscribeTo<ActualMeasurement, &AssetSimulator::onActualMeasurement>(this);
    Orchestrator::get().subscribeTo<ActualControl, &AssetSimulator::onActualControl>(this);
    Orchestrator::get().subscribeTo<DumpStateEvent, &AssetSimulator::handleDumpStateEvent>(this);
}

void AssetSimulator::onMeasurementReceived(const MeasurementReceived& info) {
    // Measurement/control received are forwarded to assets that subscribe to the id of the info, and match its destination
    std::pair<std::string, std::string> key = {info.id, info.destination};
    if (subscriptions_by_id_and_location_.contains(key)) {
        for (auto& submodel : subscriptions_by_id_and_location_[key]) {
            submodel->onUpdate(info.id, info.value, info.time_received);
        }
    }
}

void AssetSimulator::onControlReceived(const ControlReceived& info) {
    // Measurement/control received are forwarded to assets that subscribe to the id of the info, and match its destination
    std::pair<std::string, std::string> key = {info.id, info.destination};
    if (subscriptions_by_id_and_location_.contains(key)) {
        for (auto& submodel : subscriptions_by_id_and_location_[key]) {
            submodel->onUpdate(info.id, info.value, info.time_received);
        }
    }
}

void AssetSimulator::onActualMeasurement(const ActualMeasurement& info) {
    // Actual Measurement/controls are forwarded to assets that subscribe to the id of the info, and match its destination
    if (subscriptions_by_id_.contains(info.id)) {
        double time_received = Orchestrator::get().getCurrentTime();
        for (auto& model : subscriptions_by_id_[info.id]) {
            model->onUpdate(info.id, info.value, time_received);
        }
    }
}

void AssetSimulator::onActualControl(const ActualControl& info) {
    // Actual Measurement/controls are forwarded to assets that subscribe to the id of the info, and match its destination
    if (subscriptions_by_id_.contains(info.id)) {
        double time_received = Orchestrator::get().getCurrentTime();
        for (auto& model : subscriptions_by_id_[info.id]) {
            model->onUpdate(info.id, info.value, time_received);
        }
    }
}

void AssetSimulator::subscribeAssetToUpdates(const std::vector<std::string>& ids, const std::string& location, std::shared_ptr<AssetModel> model) {
    for (const auto& id : ids) {
        subscriptions_by_id_and_location_[{id, location}].push_back(model);
        subscriptions_by_id_[id].push_back(model);
    }
}

void AssetSimulator::subscribeAssetToActualUpdates(const std::vector<std::string>& ids, std::shared_ptr<AssetModel> model) {
    for (const auto& id : ids) {
        subscriptions_by_id_[id].push_back(model);
    }
}

void AssetSimulator::buildAssetModels(const nlohmann::json::basic_json::value_type& config, const InformationFlowModel& information_flow_model) {
    if (config.empty()) {
        return;
    }
    if (!config.is_array()) {
        throw std::invalid_argument("Invalid asset simulator config, must be array\n" + config.dump());
    }
    for (const auto& asset_config : config) {
        try {
            std::string type = asset_config["type"];

            switch (stringToAssetModel(type)) {
                case AssetModels::OverloadAlarm: {
                    auto asset = std::make_shared<OverloadAlarm>(information_flow_model, asset_config);
                    asset_models.push_back(asset);

                    // Temperature probe only subsribes to actual/physical updates
                    std::vector<std::string> subscriptions = asset->getSubscriptions();
                    subscribeAssetToActualUpdates(subscriptions, asset);
                    break;
                }
                case AssetModels::SubstationAlarm: {
                    auto asset = std::make_shared<SubstationAlarm>(information_flow_model, asset_config);
                    asset_models.push_back(asset);

                    std::string location = asset->getLocation();
                    std::vector<std::string> subscriptions = asset->getSubscriptions();
                    subscribeAssetToUpdates(subscriptions, location, asset);
                    break;
                }
                case AssetModels::Recloser: {
                    auto asset = std::make_shared<Recloser>(asset_config);
                    asset_models.push_back(asset);

                    // No subscription
                    break;
                }
                case AssetModels::ValueHolder: {
                    auto asset = std::make_shared<ValueHolder>(information_flow_model, asset_config);
                    asset_models.push_back(asset);

                    std::string location = asset->getLocation();
                    std::vector<std::string> subscriptions = asset->getSubscriptions();
                    subscribeAssetToUpdates(subscriptions, location, asset);
                    break;
                }
                default:
                    throw;
            }
        } catch (const nlohmann::detail::type_error& e) {
            throw std::invalid_argument("Invalid config: " + std::string(e.what()) + " in:\n" + asset_config.dump());
        }
    }
}

void AssetSimulator::handleDumpStateEvent(const DumpStateEvent& event) {
    std::ostringstream bin(std::ios::binary);
    ser20::BinaryOutputArchive archive(bin);
    archive(*this);
    logger_.saveDump("AssetSimulator", event.time, bin.str());
}

