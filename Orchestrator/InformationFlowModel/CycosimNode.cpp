/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "CycosimNode.h"
#include "Information.h"
#include "Orchestrator.h"


CycosimNode::CycosimNode(std::string name, std::string type) :
CommunicationNode(name, type) {
    //
}

bool CycosimNode::apply(MeasurementReceived& info) {
    // Don't apply own ifl functions and directly forward to Cycosim

    auto measurement = CycosimMeasurementReceived(name_, std::move(info));
    Orchestrator::get().emitLater(std::move(measurement), info.time_received);

    // Always drop since it is forwarded to Cycosim
    return true;
}

bool CycosimNode::apply(ControlReceived& info) {
    // Don't apply own ifl functions and directly forward to Cycosim

    auto control = CycosimControlReceived(name_, std::move(info));
    Orchestrator::get().emitLater(std::move(control), info.time_received);

    // Always drop since it is forwarded to Cycosim
    return true;
}

bool CycosimNode::apply(AcknowledgementReceived& info) {
    // Don't apply own ifl functions and directly forward to Cycosim
    auto acknowledgement = CycosimAcknowledgementReceived(name_, info);
    Orchestrator::get().emitLater(std::move(acknowledgement), info.time_received);

    // Always drop since it is forwarded to Cycosim
    return true;
}
