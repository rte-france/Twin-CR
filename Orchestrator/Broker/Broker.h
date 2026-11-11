/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef BROKER_INTERNAL_INTERFACE_H
#define BROKER_INTERNAL_INTERFACE_H

#include "Information.h"
#include "RingBuffer.h"
#include "NatsHelper.h"

#include <nats.h>

#include <memory>
#include <mutex>
#include <optional>
#include <thread>
#include <unordered_set>

/**
 * Class responsible for exchanging informations between the orchestrator and the external systems (except Dynawo)
 */
class Broker {
    public:
        static Broker& get() {
            static Broker instance;
            return instance;
        }

        void init();

        void subscribe(const std::string& topic, Handler handler);

        void add_dsl_subscription(const std::string& id) {
            std::lock_guard<std::mutex> lock(mutex_);
            dsl_subscriptions_.insert(id);
        }

        void remove_dsl_subscription(const std::string& id) {
            std::lock_guard<std::mutex> lock(mutex_);
            dsl_subscriptions_.erase(id);
        }

        void publishIntermediaryMeasurement(const MeasurementReceived& info, const std::string& location);
        void publishIntermediaryControl(const ControlReceived& info, const std::string& location);
        void publishIntermediaryAcknowledgement(const AcknowledgementReceived& info, const std::string& location);

    private:
        Broker();
        ~Broker();

        void onMeasurementReceived(const MeasurementReceived& info);
        void onControlReceived(const ControlReceived& info);
        void onAcknowledgementReceived(const AcknowledgementReceived& info);
        void onActualMeasurement(const ActualMeasurement& info);
        void onActualControl(const ActualControl& info);
        void onTimeUpdate(const TimeUpdate& info);
        void onDynawoTimelineEvent(const DynawoTimelineEvent& info);
        void onDynawoConstraintEvent(const DynawoConstraintEvent& info);

        void sendInformationToPerformanceBroker(MessageType type, const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::string& topic, const std::optional<tase2::Tase2Extension>& tase2_data, double time_received, const std::optional<std::string>& location, double control_time_sent = 0, int64_t control_uid = 0);

        void sendValueToPerformanceBroker(MessageType type, const std::string& id, const Value& value, double time, const std::string& topic);

        void sendValueToDslServer(const ActualValue& info);

        std::unique_ptr<RingBuffer> ring_buffer_;
        natsConnection* nats_connection_;
        std::thread performance_broker_;
        std::unordered_set<std::string> dsl_subscriptions_;
        std::mutex mutex_;
};

#endif // BROKER_INTERNAL_INTERFACE_H
