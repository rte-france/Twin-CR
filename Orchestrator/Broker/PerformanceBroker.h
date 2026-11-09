/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef PERFORMANCE_BROKER_H
#define PERFORMANCE_BROKER_H

#include "RingBuffer.h"

#include <fmt/core.h>
#include <nlohmann/json.hpp>
#include <nats.h>

/**
 * Broker that is run in a separate thread for performance reasons. Can only publish MeasurementReceived, ControlReceived, AcknowledgementReceived (SCADA messages),
 * ActualMeasurement, and ActualControl (Game Master messages) (messages that are sent with a high frequency (particularly MeasurementReceived
 * and ActualMeasurement)). Cannot subscribe to messages.
 * Receives data from the Broker through a RingBuffer (Broker writes in the buffer, PerformanceBroker reads it), then formats it
 * before sending it to the NATS server.
 */
class PerformanceBroker {
    public:
        explicit PerformanceBroker(RingBuffer* ring_buffer);

        ~PerformanceBroker();

        void readMessages();

    private:
        void handleMessage(const Message& message);

        void handleGameMasterMessage(const Message& message);
        void handleScadaMessage(const Message& message);
        void handleAcknowledgementMessage(const Message& message);

        RingBuffer* ring_buffer_;
        natsConnection* nats_connection_;
        double init_seconds_since_epoch_;
        std::string sanitized_topic_string_;
        std::string sanitized_location_string_;
        fmt::memory_buffer topic_buffer_;
        fmt::memory_buffer message_string_buffer_;
};

#endif // PERFORMANCE_BROKER_H
