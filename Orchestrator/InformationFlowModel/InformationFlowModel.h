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
        void handleAcknowledgementSent(const AcknowledgementSent& info);

        /**
         * Automatically acknowledge a control that reached its destination: an AcknowledgementSent is emitted
         * from the control's destination back to its source
         */
        void onControlReceived(const ControlReceived& info);

        /**
         * Handle a real-time critical control (control.flags.real_time_critical). Thread-safe, meant to be called
         * directly from the thread that received the control (e.g. the HMI interface's NATS thread), without
         * going through the event queue.
         * The delay, drop and corruption functions are applied to the control and, if it is not dropped, to its
         * acknowledgement, at once. The acknowledgement is returned to the caller (nullopt if the control or its
         * acknowledgement is dropped), which is responsible for applying its delay (acknowledgement->time_received).
         * The control itself, and the acknowledgement for logging purposes, are then scheduled in the event queue
         * as usual (the acknowledgement is not delivered to other modules, as the caller already got it).
         */
        std::optional<AcknowledgementReceived> handleRealTimeCriticalControl(const ControlSent& control);

        /**
         * Build the acknowledgement of 'control' (sent at control.time_received, from control's destination to its source).
         * nullopt if the control has no source (empty path)
         */
        std::optional<AcknowledgementSent> makeAcknowledgement(const ControlReceived& control) const;

        /**
         * Name of the node the information 'info' was sent from (nullopt if its path is empty)
         */
        std::optional<std::string> getSourceName(const Information& info) const;
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
         * Path back from the destination of 'info' to its source (graph links are bidirectional and routes unique)
         */
        static std::vector<graaf::vertex_id_t> getReturnPath(const Information& info) {
            return std::vector<graaf::vertex_id_t>(info.path.rbegin(), info.path.rend());
        }

        /**
         * Set the characteristics of the node with name "node_name". The characteristics are read from the "characteristics" json.
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void addCharacteristicsToNode(const std::string& node_name, const nlohmann::json::basic_json::value_type& characteristics, Mode mode=Mode::Execute) {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            network_graph_->addCharacteristicsToNode(node_name, characteristics, mode);
        }

        /**
         * Set the characteristics of the link from "source" to "destination". The characteristics are read from the "characteristics" json.
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void addCharacteristicsToLink(const std::string& source, const std::string& destination, const nlohmann::json::basic_json::value_type& characteristics, Mode mode=Mode::Execute) {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            network_graph_->addCharacteristicsToLink(source, destination, characteristics, mode);
        }

        nlohmann::json getLinkConfig(const std::string& source, std::string destination) {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            return network_graph_->getLinkConfig(source, destination);
        }

        std::vector<std::string> listNodes() {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            return network_graph_->listNodes();
        }

        std::vector<std::string> listDestinations(const std::string& source) {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            return network_graph_->listDestinations(source);
        }

        std::string getNodeType(const std::string& node_name) {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            return network_graph_->getNodeType(node_name);
        }

        nlohmann::json getNodeConfig(const std::string& node_name) {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            return network_graph_->getNodeConfig(node_name);
        }

        nlohmann::json getPathConfig(const std::string& source, const std::string& destination) {
            std::lock_guard<std::recursive_mutex> lock(mutex_);
            return network_graph_->getPathConfig(source, destination);
        }

        /**
         * New unique identifier for a control (ControlSent::control_uid). Thread-safe.
         */
        int64_t nextControlUid() { return network_graph_->nextControlUid(); }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(network_graph_);
        }

    private:
        void initSubscriptions();

        std::unique_ptr<NetworkGraph> network_graph_;
        // Protects the network graph (and the state of its delay/drop/corruption functions) against concurrent propagation of events and configuration changes
        // Recursive as propagating an event can synchronously generate others
        std::recursive_mutex mutex_;
        std::unordered_set<std::string> cycosim_nodes_;
        ClickHouseLogger& logger_;
};
CHECK_SERIALIZABLE(InformationFlowModel);

#endif // INFORMATION_FLOW_MODEL_H
