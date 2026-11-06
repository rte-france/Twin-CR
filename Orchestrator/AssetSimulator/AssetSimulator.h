/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef ASSET_SIMULATOR_H
#define ASSET_SIMULATOR_H

#include "SerialisationHelper.h"
#include "AssetModels/AssetModel.h"
#include "ClickHouseLogger.h"
#include "InformationFlowModel.h"

#include <memory>
#include <toml++/toml.h>
#include <unordered_map>


class AssetSimulator {
    public:
        AssetSimulator(const InformationFlowModel& information_flow_model, ClickHouseLogger& logger);
        AssetSimulator(ClickHouseLogger& logger, double time);

        template<class Archive>
        void serialize(Archive& ar) {
            ar(asset_models, subscriptions_by_id_, subscriptions_by_id_and_location_);
        }

    private:
        /**
         * Add an AssetModel to the AssetSimulator subscriber lists, such that the AssetModel is
         * updated each time a measurement or control with a given ID is received (either
         * MeasurementReceived or ActualMeasurement/Control).
         */
        void subscribeAssetToUpdates(const std::vector<std::string>& ids, const std::string& location, std::shared_ptr<AssetModel> model);

        /**
         * Add an AssetModel to the AssetSimulator subscriber lists, such that the AssetModel is
         * updated each time a measurement or control with a given ID is received (from
         * ActualMeasurement/Control only).
         */
        void subscribeAssetToActualUpdates(const std::vector<std::string>& ids, std::shared_ptr<AssetModel> model);

        void initSubscriptions();
        void onMeasurementReceived(const MeasurementReceived& info);
        void onControlReceived(const ControlReceived& info);
        void onActualMeasurement(const ActualMeasurement& info);
        void onActualControl(const ActualControl& info);

        void handleDumpStateEvent(const DumpStateEvent& event);

        void buildAssetModels(const nlohmann::json::basic_json::value_type& config, const InformationFlowModel& information_flow_model);

        std::vector<std::shared_ptr<AssetModel>> asset_models;
        std::unordered_map<std::string, std::vector<std::shared_ptr<AssetModel>>> subscriptions_by_id_;
        std::unordered_map<std::pair<std::string, std::string>, std::vector<std::shared_ptr<AssetModel>>, PairHash> subscriptions_by_id_and_location_;
        ClickHouseLogger& logger_;
};

CHECK_SERIALIZABLE(AssetSimulator);

#endif // ASSET_SIMULATOR_H
