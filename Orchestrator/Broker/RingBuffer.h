/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include "Tase2.h"
#include <atomic>
#include <condition_variable>
#include <mutex>

// Ring buffer sized to make a one second of buffer at max throughput (500k GM messages + 500k InformationReceived)
// This 1s buffer smoothen the bursts of messages created by Dynawo (that typically publish all messages with a period of 1s)
constexpr size_t RING_SIZE = 1 << 20; // must be power of 2, 2^20=1M

enum class MessageType {
    ActualMeasurement,
    ActualControl,
    MeasurementReceived,
    ControlReceived,
    AcknowledgementReceived
};

struct Message {
    MessageType type;
    char id[128];
    Value value;
    double time_sent;
    char destination[64];
    char topic[64];
    double time_received;
    double control_time_sent;  // Only set for AcknowledgementReceived
    int64_t control_uid;  // Only set for AcknowledgementReceived

    // Tase2 extension
    bool has_tase2;
    char tase2_id[64];
    tase2::SignalisationType signalisation_type;
    int cause;
    int validity;
    bool operator_blocked;

    // Intermediary info
    bool has_location;
    char location[64];
};

struct RingBuffer {
    std::atomic<size_t> head;
    std::atomic<size_t> tail;
    std::atomic<bool> done;
    // Mutex only used when head == tail, the ring buffer is lock-free the rest of the time
    std::mutex mutex;
    std::condition_variable not_full;
    std::condition_variable not_empty;
    Message buffer[RING_SIZE];
};

#endif // RING_BUFFER_H
