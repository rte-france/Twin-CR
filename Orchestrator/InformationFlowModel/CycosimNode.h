/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef CYCOSIM_NODE_H
#define CYCOSIM_NODE_H

#include "CommunicationNodes.h"
#include "Information.h"

#include <ser20/types/base_class.hpp>


class CycosimNode : public CommunicationNode {
    public:
        CycosimNode(std::string name, std::string typ);
        CycosimNode() = default;  // Default constructor needed for deserialization

        virtual bool apply(MeasurementReceived& info) override;
        virtual bool apply(ControlReceived& info) override;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<CommunicationNode>(this));
        }
};
SER20_REGISTER_TYPE(CycosimNode);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(CycosimNode);

#endif // CYCOSIM_NODE_H
