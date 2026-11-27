/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef CYCOSIM_INTERFACE_H
#define CYCOSIM_INTERFACE_H

#include "CycosimSocket.h"
#include "Information.h"
#include "InformationFlowModel.h"

#include <deque>
#include <string>
#include <unordered_set>

#include <fmt/core.h>
#include <nlohmann/json.hpp>

/**
 * Class responsible for implementing the control signals sent from the Game
 * Master and interfacing with the Cycosim simulation via ZMQ.
 */
class CycosimInterface {
public:
    CycosimInterface(nlohmann::json cycosim_config, InformationFlowModel& information_flow_model);

    ~CycosimInterface();

private:
    /**
     * Launch Cycosim and schedule the next time step event
     */
    void initCycosim();

    /**
     * Notify Cycosim that the next time step has started.
     */
    void goToNextTimeStep();

    /**
     * Send events to Cycosim
     */
    void sendEventsToCycosim();

    void receiveMessagesFromCycosim();

    /**
     * Parse a message received from Cycosim
     */
    void parseCycosimMessage(nlohmann::json message);

    /**
     * Callback for ActualMeasurement events - forwards to Cycosim if in
     * forward_set_
     */
    void onActualMeasurement(const ActualMeasurement& info);

    /**
     * Send a Dynawo Measurement to Cycosim
     * The command is actually saved in a queue, and will be sent to Cycosim on
     * the next goToNextTimeStep() call
     * @param info MeasurementSent event to send
     */
    void sendActualMeasurement(const ActualMeasurement& info);

    /**
     * Send a CycosimMeasurementReceived event to Cycosim
     * The command is actually saved in a queue, and will be sent to Cycosim on
     * the next goToNextTimeStep() call
     * @param info MeasurementSent event to send
     */
    void sendMeasurement(const CycosimMeasurementReceived& info);

    /**
     * Send a CycosimControlReceived event to Cycosim
     * The command is actually saved in a queue, and will be sent to Cycosim on
     * the next goToNextTimeStep() call
     * @param info ControlSent event to send
     */
    void sendControl(const CycosimControlReceived& info);

    /**
     * Send a CycosimAcknowledgementReceived event (acknowledgement of a control sent from Cycosim) to Cycosim
     * The acknowledgement is actually saved in a queue, and will be sent to Cycosim on
     * the next goToNextTimeStep() call
     */
    void sendAcknowledgement(const CycosimAcknowledgementReceived& info);

    /**
     * Queue an acknowledgement for Cycosim
     */
    void queueAcknowledgement(const AcknowledgementReceived& info, const std::string& source);

    // Configuration
    nlohmann::json config_;
    double period_;
    double start_time_ = 0.0;
    unsigned long tick_index_ = 1;
    double next_sync_time_ = 0.0;
    double init_seconds_since_epoch_;
    fmt::memory_buffer message_string_buffer_;
    // Forwarding configuration: list of dynawo ids to forward to Cycosim
    std::unordered_set<std::string> forward_set_;
    std::unordered_set<std::string> cycosim_nodes_;
    std::unordered_map<std::string, std::string> topic_map_;

    CycosimSocket socket_;

    InformationFlowModel& information_flow_model_;

    std::deque<nlohmann::json> to_publish_;
};

#endif  // CYCOSIM_INTERFACE_H
