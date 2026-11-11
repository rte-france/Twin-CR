/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef COMMUNICATION_ELEMENTS_H
#define COMMUNICATION_ELEMENTS_H

#include "CorruptionFunctions.h"
#include "DelayFunctions.h"
#include "DropFunctions.h"
#include "Information.h"

#include "SerialisationHelper.h"
#include "graaflib/types.h"
#include "../utils/Mode.h"
#include <ser20/types/polymorphic.hpp>

#include <cstddef>
#include <memory>
#include <optional>
#include <vector>
#include <nlohmann/json.hpp>

class MonitoredPath;

/**
 * Abstract class for CommunicationLinks and CommunicationNodes
 */
class CommunicationElement {
    public:
        CommunicationElement() = default;
        virtual ~CommunicationElement() = default;  // Abstract class
        CommunicationElement(const CommunicationElement&) = delete;  // Avoid accidental slicing
        CommunicationElement& operator=(const CommunicationElement&) = delete;

        /**
         * Apply the delay, drop, and corruption functions of this element to info.
         * Returns 1 if the info is dropped, else 0.
         * The information (value, and time_received) is modified in place.
         */
        virtual bool apply(MeasurementReceived& info);

        /**
         * Apply the delay, drop, and corruption functions of this element to info.
         * Returns 1 if the info is dropped, else 0.
         * The information (value, and time_received) is modified in place.
         */
        virtual bool apply(ControlReceived& info);

        /**
         * Apply the delay, drop, and corruption functions of this element to info.
         * Returns 1 if the info is dropped, else 0.
         * The information (value, and time_received) is modified in place.
         */
        virtual bool apply(AcknowledgementReceived& info);

        /**
         * Set the delay function of the element, based on the function_config json
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void setDelayFunction(const nlohmann::json::basic_json::value_type& function_config, Mode mode=Mode::Execute);

        /**
         * Set the drop function of the element, based on the function_config json
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void setDropFunction(const nlohmann::json::basic_json::value_type& function_config, Mode mode=Mode::Execute);

        /**
         * Set the corruption function of the element, based on the function_config json
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void addCorruptionFunction(const nlohmann::json::basic_json::value_type& function_config, Mode mode=Mode::Validate);

        void clearCorruptionFunctions(Mode mode=Mode::Validate);

        nlohmann::json getDelayFunctionConfig() const { return delay_function_config_; }

        nlohmann::json getDropFunctionConfig() const { return drop_function_config_; }

        nlohmann::json getCorruptionFunctionConfigs() const { return corruption_function_configs_; }

        nlohmann::json getElementConfig() const {
            nlohmann::json config = {
                {"delay_function", delay_function_config_},
                {"drop_function", drop_function_config_},
                {"corruption_functions", getCorruptionFunctionConfigs()},
            };
            return config;
        }

        void addObserver(std::shared_ptr<MonitoredPath> path) {
            observers_.push_back(path);
        }

        void setAvailable(bool available);

        bool isAvailable() const { return available_; }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(delay_function_, drop_function_, corruption_functions_, seed_, observers_, available_, delay_function_config_, drop_function_config_, corruption_function_configs_);
        }

    protected:
        template <typename T>
        bool genericApply(T& info) {
            if (drop_function_) {
                bool dropped = (*drop_function_)->apply(info.time_received);
                if (dropped) {
                    return 1;
                }
            }

            if (delay_function_) {
                (*delay_function_)->apply(info);
            }

            for (auto& corruption_function : corruption_functions_) {
                corruption_function->apply(info);
            }

            return 0;
        }

        std::optional<std::shared_ptr<DelayFunction>> delay_function_;
        std::optional<std::shared_ptr<DropFunction>> drop_function_;
        std::vector<std::shared_ptr<CorruptionFunction>> corruption_functions_;
        size_t seed_;

    private:
        void notifyObservers();

        std::vector<std::shared_ptr<MonitoredPath>> observers_;
        bool available_ = true;
        nlohmann::json delay_function_config_ = {};
        nlohmann::json drop_function_config_ = {};
        std::vector<nlohmann::json> corruption_function_configs_;
};
SER20_REGISTER_TYPE(CommunicationElement);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(CommunicationElement);

class NetworkGraph;

class MonitoredPath : public std::enable_shared_from_this<MonitoredPath> {
    public:
        /**
         * Creates a MonitoredPath between source and destination.
         * Whenever, the path becomes available (i.e. all elements of the path are available, this includes communication links in both directions)
         * a GI (general interrogation) is sent from source to destination.
         * The destination is expected to resend all the TSes it has in memory when receiving a GI.
         * Always created as a shared_ptr as MonitoredPaths require shared_from_this.
         */
        static std::shared_ptr<MonitoredPath> create(const std::string& source, const std::string& destination, NetworkGraph& network_graph) {
            auto monitored_path = std::shared_ptr<MonitoredPath>(
                new MonitoredPath(source, destination, network_graph)
            );
            monitored_path->init(network_graph);
            return monitored_path;
        }
        MonitoredPath() = default;  // Default constructor needed for deserialization

        void onElementAvailabilityChanged() {
            updateAvailability();
        }

        bool isAvailable() const { return available_; }

        // Restores the back-pointer to the graph owning this path after deserialization
        void setNetworkGraph(NetworkGraph& network_graph) { network_graph_ = &network_graph; }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(destination_, path_, available_, elements_);
        }

    private:
        // Private constructor to ensure MonitoredPath is always created as a shared_ptr
        MonitoredPath(const std::string& source, const std::string& destination, NetworkGraph& network_graph);
        // Two-part construction as shared_from_this() can only be called after the constructor has returned
        void init(NetworkGraph& network_graph);

        void updateAvailability();

        std::string destination_;
        std::vector<graaf::vertex_id_t> path_;
        bool available_;
        std::vector<std::shared_ptr<CommunicationElement>> elements_;
        NetworkGraph* network_graph_ = nullptr;  // Graph owning this path, used to get the uid of the GIs
};

#endif // COMMUNICATION_ELEMENTS_H
