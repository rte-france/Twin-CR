/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Broker.h"
#include "Credentials.h"
#include "Information.h"
#include "Orchestrator.h"
#include "PerformanceBroker.h"
#include "RingBuffer.h"
#include "Tase2.h"

#include <cstring>
#include <memory>
#include <optional>
#include <stdexcept>
#include <thread>

#include <fmt/core.h>
#include <spdlog/spdlog.h>

/**
 * Helper function to copy a std::string into a fixed-size char array field of the ring buffer.
 * Throws if the string would overflow (accounting for the terminating null)
 */
template <size_t N>
inline void copy_string(char (&dst)[N], const std::string& src) {
    if (src.size() >= N) {
        throw std::runtime_error(
            "String '" + src + "' is " + std::to_string(src.size()) +
            " characters long, exceeding the " + std::to_string(N - 1) + "-character limit of this field"
        );
    }
    std::memcpy(dst, src.data(), src.size());
    dst[src.size()] = '\0';
}

void launch_performance_broker(RingBuffer* ring_buffer) {
    auto performance_broker = PerformanceBroker(ring_buffer);
    performance_broker.readMessages();
}

Broker::Broker() {
    // Connect to NATS server
    nats_connection_ = nullptr;
    natsStatus s = natsConnection_ConnectTo(&nats_connection_, Credentials::get().getNatsURL());
    if (s != NATS_OK) {
       throw std::runtime_error("Connect failed: " + std::string(natsStatus_GetText(s)));
    }

    // Set up high-frequency publications through the PerformanceBroker
    ring_buffer_ = std::make_unique<RingBuffer>();
    ring_buffer_->head = 0;
    ring_buffer_->tail = 0;

    // Initialize the performance broker (must be done after the creation of the RingBuffer)
    performance_broker_ = std::thread(launch_performance_broker, ring_buffer_.get());
}

void Broker::init() {
    Orchestrator::get().subscribeTo<TimeUpdate, &Broker::onTimeUpdate>(this);
    Orchestrator::get().subscribeTo<DynawoTimelineEvent, &Broker::onDynawoTimelineEvent>(this);
    Orchestrator::get().subscribeTo<DynawoConstraintEvent, &Broker::onDynawoConstraintEvent>(this);
    Orchestrator::get().subscribeTo<ActualMeasurement, &Broker::onActualMeasurement>(this);
    Orchestrator::get().subscribeTo<ActualControl, &Broker::onActualControl>(this);
    Orchestrator::get().subscribeTo<MeasurementReceived, &Broker::onMeasurementReceived>(this);
    Orchestrator::get().subscribeTo<ControlReceived, &Broker::onControlReceived>(this);
    Orchestrator::get().subscribeTo<AcknowledgementReceived, &Broker::onAcknowledgementReceived>(this);
}

Broker::~Broker() {
    ring_buffer_->done.store(true, std::memory_order_release);
    ring_buffer_->not_empty.notify_all();
    performance_broker_.join();

    spdlog::info("Sending stop signal");
    // Send message with "stop" subject to tell all listening applications to terminate
    natsStatus s = natsConnection_PublishString(nats_connection_, "stop", R"({"status": "Stopped"})");
    if (s != NATS_OK) {
        std::cerr << "Publish failed: " << natsStatus_GetText(s) << std::endl;
    }

    if (nats_connection_ != nullptr) {
        natsConnection_Destroy(nats_connection_);
    }
}

void Broker::onActualMeasurement(const ActualMeasurement& info) {
    sendValueToPerformanceBroker(MessageType::ActualMeasurement, info.id, info.value, info.time, info.topic);
    bool has_dsl_subscription;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        has_dsl_subscription = dsl_subscriptions_.contains(info.id);
    }
    if (has_dsl_subscription) {
        sendValueToDslServer(info);
    }
}

void Broker::onActualControl(const ActualControl& info) {
    // Controls do not have a high-frequency, but still sent to the PerformanceBroker with Measurements for consistency with measurements
    sendValueToPerformanceBroker(MessageType::ActualControl, info.id, info.value, info.time, info.topic);
    bool has_dsl_subscription;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        has_dsl_subscription = dsl_subscriptions_.contains(info.id);
    }
    if (has_dsl_subscription) {
        sendValueToDslServer(info);
    }
}

void Broker::onMeasurementReceived(const MeasurementReceived& info) {
    sendInformationToPerformanceBroker(MessageType::MeasurementReceived, info.id, info.value, info.time_sent, info.destination, info.topic, info.tase2_data, info.time_received, std::nullopt);
}

void Broker::onControlReceived(const ControlReceived& info) {
    // Controls do not have a high-frequency, but still sent to the PerformanceBroker with Measurements for consistency with measurements
    sendInformationToPerformanceBroker(MessageType::ControlReceived, info.id, info.value, info.time_sent, info.destination, info.topic, info.tase2_data, info.time_received, std::nullopt);
}

void Broker::onAcknowledgementReceived(const AcknowledgementReceived& info) {
    if (info.flags.real_time_critical) {
        return;  // Already returned to the caller of the real-time critical control
    }
    sendInformationToPerformanceBroker(MessageType::AcknowledgementReceived, info.id, info.value, info.time_sent, info.destination, info.topic, info.tase2_data, info.time_received, std::nullopt, info.control_time_sent, info.control_uid);
}

void Broker::publishIntermediaryMeasurement(const MeasurementReceived& info, const std::string& location) {
    sendInformationToPerformanceBroker(MessageType::MeasurementReceived, info.id, info.value, info.time_sent, info.destination, info.topic, info.tase2_data, info.time_received, location);
}
void Broker::publishIntermediaryControl(const ControlReceived& info, const std::string& location) {
    sendInformationToPerformanceBroker(MessageType::ControlReceived, info.id, info.value, info.time_sent, info.destination, info.topic, info.tase2_data, info.time_received, location);
}
void Broker::publishIntermediaryAcknowledgement(const AcknowledgementReceived& info, const std::string& location) {
    sendInformationToPerformanceBroker(MessageType::AcknowledgementReceived, info.id, info.value, info.time_sent, info.destination, info.topic, info.tase2_data, info.time_received, location, info.control_time_sent, info.control_uid);
}

void Broker::onTimeUpdate(const TimeUpdate& info) {
    std::string time_msg = fmt::format("{{\"current_time\": {}}}", info.value);
    natsStatus s = natsConnection_PublishString(nats_connection_, "time", time_msg.c_str());
    if (s != NATS_OK) {
        spdlog::error("Broker: Failed to publish time update: {}", natsStatus_GetText(s));
    }
}

void Broker::onDynawoTimelineEvent(const DynawoTimelineEvent& info) {
    natsConnection_PublishString(nats_connection_, "Dynawo.Timeline", info.event_string.c_str());
}

void Broker::onDynawoConstraintEvent(const DynawoConstraintEvent& info) {
    natsConnection_PublishString(nats_connection_, "Dynawo.Constraints", info.event_string.c_str());
}

void Broker::subscribe(const std::string& topic, Handler handler) {
    auto handler_ptr = std::make_shared<Handler>(std::move(handler));
    nats_handlers_.push_back(handler_ptr);

    natsSubscription *sub = nullptr;
    natsStatus s = natsConnection_Subscribe(&sub, nats_connection_, topic.c_str(), NatsMessageHandlerWrapper, handler_ptr.get());

    if (s != NATS_OK) {
        throw std::runtime_error("Subscription failed: " + std::string(natsStatus_GetText(s)));
    }
}

void Broker::sendInformationToPerformanceBroker(MessageType type, const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::string& topic, const std::optional<tase2::Tase2Extension>& tase2_data, double time_received, const std::optional<std::string>& location, double control_time_sent, int64_t control_uid) {
    size_t head = ring_buffer_->head.load(std::memory_order_relaxed);
    size_t tail = ring_buffer_->tail.load(std::memory_order_acquire);
    size_t next_head = (head + 1) % RING_SIZE;
    const bool was_empty = (head == tail);

    if (next_head == tail) {
        // Buffer is full — wait (reader too slow or not running)
        // Use a condition variable instead of spin-wait (std::this_thread::yield) to avoid starving the reader on few-core machines.
        std::unique_lock<std::mutex> lock(ring_buffer_->mutex);
        ring_buffer_->not_full.wait(lock, [&]() {
            tail = ring_buffer_->tail.load(std::memory_order_acquire);
            return next_head != tail;
        });
    }

    Message& msg = ring_buffer_->buffer[head % RING_SIZE];
    msg.type = type;
    copy_string(msg.id, id);
    msg.value = value;
    msg.time_sent = time_sent;
    copy_string(msg.destination, destination);
    copy_string(msg.topic, topic);
    msg.time_received = time_received;
    msg.control_time_sent = control_time_sent;
    msg.control_uid = control_uid;
    // Tase2 extension
    msg.has_tase2 = tase2_data.has_value();
    if (tase2_data.has_value()) {
        copy_string(msg.tase2_id, tase2_data->tase2_id);
        msg.signalisation_type = tase2_data->signalisation_type;
        msg.cause = tase2_data->cause;
        msg.validity = tase2_data->validity;
        msg.operator_blocked = tase2_data->operator_blocked;
    }

    if (location.has_value()) {
        msg.has_location = true;
        copy_string(msg.location, location.value());
    } else {
        msg.has_location = false;
    }

    ring_buffer_->head.store((head + 1) % RING_SIZE, std::memory_order_release);
    if (was_empty) {
        ring_buffer_->not_empty.notify_one();
    }
}

void Broker::sendValueToPerformanceBroker(MessageType type, const std::string& id, const Value& value, double time, const std::string& topic) {
    size_t head = ring_buffer_->head.load(std::memory_order_relaxed);
    size_t tail = ring_buffer_->tail.load(std::memory_order_acquire);
    size_t next_head = (head + 1) % RING_SIZE;
    const bool was_empty = (head == tail);

    if (next_head == tail) {
        // Buffer is full — wait (reader too slow or not running)
        // Use a condition variable instead of spin-wait (std::this_thread::yield) to avoid starting the reader on few-core machines.
        std::unique_lock<std::mutex> lock(ring_buffer_->mutex);
        ring_buffer_->not_full.wait(lock, [&]() {
            tail = ring_buffer_->tail.load(std::memory_order_acquire);
            return next_head != tail;
        });
    }

    Message& msg = ring_buffer_->buffer[head % RING_SIZE];
    msg.type = type;
    copy_string(msg.id, id);
    msg.value = value;
    msg.time_sent = time;
    copy_string(msg.topic, topic);

    ring_buffer_->head.store((head + 1) % RING_SIZE, std::memory_order_release);
    if (was_empty) {
        ring_buffer_->not_empty.notify_one();
    }
}

void Broker::sendValueToDslServer(const ActualValue& info) {
    std::string message_string = fmt::format(
R"({{
    "id": "{}",
    "value": {},
    "time": {}
}})", info.id, info.value, info.time);
    natsConnection_PublishString(nats_connection_, "DSL_values", message_string.c_str());
}
