/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "PerformanceBroker.h"
#include "Credentials.h"
#include "NatsHelper.h"
#include "Orchestrator.h"
#include "RingBuffer.h"

#include <cstddef>
#include <cstring>
#include <mutex>

#include <fmt/core.h>

PerformanceBroker::PerformanceBroker(RingBuffer* ring_buffer) : ring_buffer_(ring_buffer) {
    init_seconds_since_epoch_ = std::chrono::duration_cast<std::chrono::duration<double>>(Orchestrator::get().getInitialClockTime().time_since_epoch()).count();

    // Connect to NATS server
    nats_connection_ = nullptr;
    natsStatus s = natsConnection_ConnectTo(&nats_connection_, Credentials::get().getNatsURL());
    if (s != NATS_OK) {
       throw std::runtime_error("Connect failed: " + std::string(natsStatus_GetText(s)));
    }
    topic_buffer_.reserve(128);
    message_string_buffer_.reserve(256);
}

PerformanceBroker::~PerformanceBroker() {
    natsConnection_Destroy(nats_connection_);
}

void PerformanceBroker::readMessages() {
    Message msg;
    while (true) {
        size_t tail = ring_buffer_->tail.load(std::memory_order_relaxed);
        size_t head = ring_buffer_->head.load(std::memory_order_acquire);

        if (tail == head) {
            if (ring_buffer_->done.load(std::memory_order_acquire)) {
                break;
            }
            // Buffer is empty — wait
            std::unique_lock<std::mutex> lock(ring_buffer_->mutex);
            ring_buffer_->not_empty.wait_for(lock, std::chrono::milliseconds(100), [&]() {
                head = ring_buffer_->head.load(std::memory_order_acquire);
                return tail != head || ring_buffer_->done.load(std::memory_order_acquire);
            });
            continue;
        }

        const bool was_full = ((head + 1) % RING_SIZE == tail);

        msg = ring_buffer_->buffer[tail % RING_SIZE];
        ring_buffer_->tail.store((tail + 1) % RING_SIZE, std::memory_order_release);
        if (was_full) {
            ring_buffer_->not_full.notify_one();
        }
        handleMessage(msg);
    }
}

void PerformanceBroker::handleMessage(const Message& message) {
    MessageType message_type = message.type;
    switch (message_type) {
        case MessageType::ActualMeasurement:
        case MessageType::ActualControl:
            handleGameMasterMessage(message);
            break;
        case MessageType::MeasurementReceived:
        case MessageType::ControlReceived:
            handleScadaMessage(message);
            break;
        case MessageType::AcknowledgementReceived:
            handleAcknowledgementMessage(message);
            break;
        default:
            throw std::runtime_error("Unknown message type");
    }
}

void PerformanceBroker::handleGameMasterMessage(const Message& message) {
    sanitized_topic_string_.assign(message.topic);
    sanitizeNatsTopicName(sanitized_topic_string_);

    topic_buffer_.clear();
    fmt::format_to(std::back_inserter(topic_buffer_), "GameMaster.{}", sanitized_topic_string_);
    topic_buffer_.push_back('\0');

    message_string_buffer_.clear();
    fmt::format_to(std::back_inserter(message_string_buffer_),
        R"({{"id":"{}","value":{},"time":{}}})", message.id, message.value, message.time_sent);
    message_string_buffer_.push_back('\0');  // Null-termination

    natsConnection_PublishString(nats_connection_, topic_buffer_.data(), message_string_buffer_.data());
}

void PerformanceBroker::handleScadaMessage(const Message& message) {
    sanitized_topic_string_.assign(message.topic);
    sanitizeNatsTopicName(sanitized_topic_string_);

    // Location is not specified for information that have reached their destination. For those, the location is simply the destination that has been reached.
    if (message.has_location) {
        sanitized_location_string_.assign(message.location);
    } else {
        sanitized_location_string_.assign(message.destination);
    }
    sanitizeNatsTopicName(sanitized_location_string_);

    topic_buffer_.clear();
    fmt::format_to(std::back_inserter(topic_buffer_), "HMI.{}.{}", sanitized_location_string_, sanitized_topic_string_);
    topic_buffer_.push_back('\0');

    message_string_buffer_.clear();
    fmt::format_to(std::back_inserter(message_string_buffer_),
        R"({{"id":"{}","value":{},"time_sent":{},"time_received":{})",
        message.id, message.value, message.time_sent, message.time_received);

    if (message.has_tase2) {
        appendTase2Field(message_string_buffer_, message.tase2_id, message.value, message.time_sent, init_seconds_since_epoch_, message.cause, message.validity, message.operator_blocked, message.signalisation_type);
    }

    fmt::format_to(std::back_inserter(message_string_buffer_), "}}");
    message_string_buffer_.push_back('\0');

    natsConnection_PublishString(nats_connection_, topic_buffer_.data(), message_string_buffer_.data());
}

void PerformanceBroker::handleAcknowledgementMessage(const Message& message) {
    // Published on Acknowledgement.location.topic instead of HMI.location.topic
    sanitized_topic_string_.assign(message.topic);
    sanitizeNatsTopicName(sanitized_topic_string_);

    if (message.has_location) {
        sanitized_location_string_.assign(message.location);
    } else {
        sanitized_location_string_.assign(message.destination);
    }
    sanitizeNatsTopicName(sanitized_location_string_);

    topic_buffer_.clear();
    fmt::format_to(std::back_inserter(topic_buffer_), "Acknowledgement.{}.{}", sanitized_location_string_, sanitized_topic_string_);
    topic_buffer_.push_back('\0');

    message_string_buffer_.clear();
    fmt::format_to(std::back_inserter(message_string_buffer_),
        R"({{"control_uid":{},"id":"{}","value":{},"control_time_sent":{},"time_sent":{},"time_received":{}}})",
        message.control_uid, message.id, message.value, message.control_time_sent, message.time_sent, message.time_received);
    message_string_buffer_.push_back('\0');

    natsConnection_PublishString(nats_connection_, topic_buffer_.data(), message_string_buffer_.data());
}
