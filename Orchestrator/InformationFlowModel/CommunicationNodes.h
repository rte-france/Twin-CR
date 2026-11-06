/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef COMMUNICATION_NODES_H
#define COMMUNICATION_NODES_H

#include "CommunicationElements.h"
#include "Information.h"

#include "graaflib/types.h"
#include <ser20/types/base_class.hpp>

class CommunicationNode : public CommunicationElement {
    public:
        CommunicationNode(std::string name, std::string type);
        CommunicationNode() = default;  // Default constructor needed for deserialization

        std::string getName() const { return name_; }
        std::string getType() const { return type_; }

        /**
         * Apply the delay, drop, and corruption functions of this element to info.
         * Returns 1 if the info is dropped, else 0.
         * The information (value, and time_received) is modified in place.
         */
        bool apply(MeasurementReceived& info) override;

        /**
         * Apply the delay, drop, and corruption functions of this element to info.
         * Returns 1 if the info is dropped, else 0.
         * The information (value, and time_received) is modified in place.
         */
        bool apply(ControlReceived& info) override;

        void publishIntermediaryMeasurement(const MeasurementReceived& info);
        void publishIntermediaryControl(const ControlReceived& info);

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<CommunicationElement>(this), name_, type_, publish_intermediary_info_);
        }

        void setPublishIntermediaryInfo(bool value) {
            publish_intermediary_info_ = value;
        }

    protected:
        std::string name_;
        std::string type_;
        bool publish_intermediary_info_;
};
SER20_REGISTER_TYPE(CommunicationNode);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(CommunicationNode);

/**
 * Copy of the MeasurementReceived class for storage inside RTUs.
 * Avoid poluting Information.h with specific serialization functions (includes routing but not time_received)
 */
struct MeasurementReceivedCopy {
    MeasurementReceivedCopy(const MeasurementReceived& info):
        id(info.id),
        value(info.value),
        time_sent(info.time_sent),
        destination(info.destination),
        path(info.path),
        topic(info.topic),
        tase2_data(info.tase2_data) {}
        // time_received(info.time_received) {}
    MeasurementReceivedCopy() = default;  // For deserialization

    std::string id;
    Value value;
    double time_sent;
    std::string destination;
    std::vector<graaf::vertex_id_t> path;
    std::string topic;
    std::optional<tase2::Tase2Extension> tase2_data;
    // double time_received;  // Not needed

    template<class Archive>
    void serialize(Archive& ar) {
        ar(id, value, time_sent, destination, path, topic, tase2_data);
    }
};

#endif // COMMUNICATION_NODES_H
