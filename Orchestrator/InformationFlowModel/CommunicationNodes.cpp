/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "CommunicationNodes.h"
#include "Broker.h"
#include "CommunicationElements.h"
#include "Information.h"
#include "Orchestrator.h"


CommunicationNode::CommunicationNode(std::string name, std::string type) :
name_(name),
type_(type),
publish_intermediary_info_(false) {
    // Seed the element based on the name of the node
    std::hash<std::string> hasher;
    seed_ = hasher(name);
}

bool CommunicationNode::apply(MeasurementReceived& info) {
    bool dropped = CommunicationElement::apply(info);
    if (dropped) return dropped;

    // Publish intermediary info (except when info arrives at its destination since it is no longer intermediary then)
    if (publish_intermediary_info_ && info.destination != name_) {
        Orchestrator::get().scheduleEvent(
            info.time_received,
            makeCallback<&CommunicationNode::publishIntermediaryMeasurement>(this, info)
        );
    }

    return dropped;
}

bool CommunicationNode::apply(ControlReceived& info) {
    bool dropped = CommunicationElement::apply(info);
    if (dropped) return dropped;

    // Publish intermediary info (except when info arrives at its destination since it is no longer intermediary then)
    if (publish_intermediary_info_ && info.destination != name_) {
        Orchestrator::get().scheduleEvent(
            info.time_received,
            makeCallback<&CommunicationNode::publishIntermediaryControl>(this, info)
        );
    }

    return dropped;
}

void CommunicationNode::publishIntermediaryMeasurement(const MeasurementReceived& info) {
    Broker::get().publishIntermediaryMeasurement(info, name_);
}

void CommunicationNode::publishIntermediaryControl(const ControlReceived& info) {
    Broker::get().publishIntermediaryControl(info, name_);
}
