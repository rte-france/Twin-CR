/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "RTU.h"
#include "Information.h"
#include "Orchestrator.h"

#include "graaflib/types.h"
#include <memory>


RTU::RTU(std::string name, std::string type, graaf::vertex_id_t vertex_id) :
CommunicationNode(name, type) {
    vertex_id_ = vertex_id;
}

bool RTU::apply(MeasurementReceived& info) {
    bool dropped = CommunicationNode::apply(info);
    if (dropped) {
        return dropped;
    }

    // Save TS if more recent than currently saved value
    if (info.tase2_data.has_value() && info.tase2_data->signalisation_type == tase2::SignalisationType::TS) {
        if (!saved_TSes_.contains(info.id)) {
            saved_TSes_.emplace(info.id, info);
        } else {
            if (info.time_sent > saved_TSes_.at(info.id).time_sent) {
                saved_TSes_.at(info.id) = MeasurementReceivedCopy(info);
            }
        }
    }

    return dropped;
}

bool RTU::apply(ControlReceived& info) {
    bool dropped = CommunicationNode::apply(info);
    if (dropped) {
        return dropped;
    }

    // Resend saved TSes when receives a CG
    if (info.tase2_data.has_value() && info.tase2_data->signalisation_type == tase2::SignalisationType::CG && info.destination == name_) {
        for (const auto& [id, info] : saved_TSes_) {
            const auto& full_route = info.path;
            auto it = std::find(full_route.begin(), full_route.end(), vertex_id_);
            assert(it != full_route.end());  // Full route should always contain self, as an RTU only saves TSes that pass through it
            std::vector<graaf::vertex_id_t> remaining_route(it, full_route.end());

            Orchestrator::get().emit(MeasurementSent(info.id, info.value, info.time_sent, info.destination, remaining_route, info.topic, info.tase2_data));
        }
    }

    return dropped;
}
