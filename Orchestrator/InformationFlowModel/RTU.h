/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef RTU_H
#define RTU_H

#include "CommunicationNodes.h"
#include "Information.h"

#include <ser20/types/base_class.hpp>
#include <unordered_map>

class RTU : public CommunicationNode {
    public:
        RTU(std::string name, std::string type, graaf::vertex_id_t vertex_id);
        RTU() = default;  // Default constructor needed for deserialization

        virtual bool apply(MeasurementReceived& info) override;
        virtual bool apply(ControlReceived& info) override;
        virtual bool apply(AcknowledgementReceived& info) override;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<CommunicationNode>(this), saved_TSes_, vertex_id_);
        }

    private:
        std::unordered_map<std::string, MeasurementReceivedCopy> saved_TSes_;
        graaf::vertex_id_t vertex_id_;
};
SER20_REGISTER_TYPE(RTU);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(RTU);

#endif // RTU_H
