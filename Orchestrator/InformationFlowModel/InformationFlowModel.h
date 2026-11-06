/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef INFORMATION_FLOW_MODEL_H
#define INFORMATION_FLOW_MODEL_H

#include "CommunicationElements.h"
#include "Information.h"
#include "NetworkGraph.h"
#include "SerialisationHelper.h"
#include "ClickHouseLogger.h"

#include <toml++/toml.h>

#include <filesystem>
#include <memory>
#include <mutex>
#include <optional>
#include <nlohmann/json.hpp>

class InformationFlowModel {
    public:
        InformationFlowModel(bool with_subscriptions, ClickHouseLogger& logger, std::optional<nlohmann::json> cycosim_config);

        /**
         * Construct from previously dumped archive fetched from Clickhouse
         */
        InformationFlowModel(ClickHouseLogger& logger, double time);

        /**
         * Dump state to binary archive
         */
        void dumpState(const std::filesystem::path dump_path);

        void handleMeasurementSent(const MeasurementSent& info);
        void handleControlSent(const ControlSent& info);
        void handleDumpStateEvent(const DumpStateEvent& event);

        bool handleCycosimMeasurement(const MeasurementSent &info);
        bool handleCycosimControl(const ControlSent &info);

        /**
         * Apply the delay, drop, and corruption function of all CommunicationElements between the source and destination of 'info'
         */
        template<typename T>
        bool propagateInformation(T& info);

        /**
         * Get the list of vertices (by vertex_id) from the CommunicationNode with name 'source' to the one with name 'destination'
         */
        std::vector<graaf::vertex_id_t> getPath(const std::string& source, const std::string& destination) const;

        /**
         * Set the characteristics of the node with name "node_name". The characteristics are read from the "characteristics" json.
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void addCharacteristicsToNode(const std::string& node_name, const nlohmann::json::basic_json::value_type& characteristics, Mode mode=Mode::Execute) {
            std::lock_guard<std::mutex> lock(mutex_);
            network_graph_->addCharacteristicsToNode(node_name, characteristics, mode);
        }

        /**
         * Set the characteristics of the link from "source" to "destination". The characteristics are read from the "characteristics" json.
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void addCharacteristicsToLink(const std::string& source, const std::string& destination, const nlohmann::json::basic_json::value_type& characteristics, Mode mode=Mode::Execute) {
            std::lock_guard<std::mutex> lock(mutex_);
            network_graph_->addCharacteristicsToLink(source, destination, characteristics, mode);
        }

        nlohmann::json getLinkConfig(const std::string& source, std::string destination) {
            std::lock_guard<std::mutex> lock(mutex_);
            return network_graph_->getLinkConfig(source, destination);
        }

        std::vector<std::string> listNodes() {
            std::lock_guard<std::mutex> lock(mutex_);
            return network_graph_->listNodes();
        }

        std::vector<std::string> listDestinations(const std::string& source) {
            std::lock_guard<std::mutex> lock(mutex_);
            return network_graph_->listDestinations(source);
        }

        nlohmann::json getNodeConfig(const std::string& node_name) {
            std::lock_guard<std::mutex> lock(mutex_);
            return network_graph_->getNodeConfig(node_name);
        }

        nlohmann::json getPathConfig(const std::string& source, const std::string& destination) {
            std::lock_guard<std::mutex> lock(mutex_);
            return network_graph_->getPathConfig(source, destination);
        }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(network_graph_);
        }

    private:
        void initSubscriptions();

        std::unique_ptr<NetworkGraph> network_graph_;
        std::mutex mutex_;
        std::unordered_set<std::string> cycosim_nodes_;
        ClickHouseLogger& logger_;
};
CHECK_SERIALIZABLE(InformationFlowModel);

#endif // INFORMATION_FLOW_MODEL_H
