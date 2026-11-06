/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "Replay.h"
#include "Credentials.h"
#include "EventQueue.h"
#include "Information.h"
#include "Orchestrator.h"
#include "../utils/TomlExtension.h"

#include <curl/curl.h>
#include <spdlog/spdlog.h>
#include <toml++/toml.h>

#include <future>
#include <sstream>
#include <stdexcept>
#include <string>

Replay::Replay() :
simulation_name_(Orchestrator::get().getSimulationName()),
current_time_(0),
period_(get_or_throw<double>(Orchestrator::get().getConfig(), {"master", "period"})),
topic_filter_("") {
    curl_global_init(CURL_GLOBAL_ALL);
}


Replay::~Replay() {
    curl_global_cleanup();
}

void Replay::setStep(unsigned long index) {
    step_index_ = index;
    current_time_ = step_index_ * period_;
    next_time_step_ = (step_index_ + 1) * period_;
}

void Replay::setTargetTime(double time) {
    target_time_ = time;
    setStep(step_index_);
    if (next_time_step_ <= target_time_) {
        Orchestrator::get().scheduleEvent(
            next_time_step_,
            makeCallback<&Replay::goToNextTimeStep>(this)
        );
    }
}

void Replay::jumpToTime(double time) {
    target_time_ = time;

    // Go to the nearest period multiple (rounding down)
    setStep(static_cast<unsigned long>(std::floor(target_time_ / period_)));
    spdlog::warn("Replay asked to jump to time {}, jumped to nearest period {} and restarting from there", time, current_time_);
}

void Replay::goToNextTimeStep() {
    fillBuffers();

    // Empty the buffer for all event types sequentially. The order of event of a given type
    // is thus kept, but not the order of events of different types.
    // I.e. all events of type MeasurementSent (of the current period) are emitted
    // before emitting the events of type MeasurementReceived, ControlSent, etc.
    for (auto& [event_type, buffer] : buffers_) {
        const auto type = static_cast<SerializableInfo>(event_type);
        for (const auto& event : buffer) {
            switch (type) {
                case SerializableInfo::MeasurementSent:
                    Orchestrator::get().emit(*static_cast<MeasurementSent*>(event.get()));
                    break;
                case SerializableInfo::MeasurementReceived:
                    Orchestrator::get().emit(*static_cast<MeasurementReceived*>(event.get()));
                    break;
                case SerializableInfo::ControlSent:
                    Orchestrator::get().emit(*static_cast<ControlSent*>(event.get()));
                    break;
                case SerializableInfo::ControlReceived:
                    Orchestrator::get().emit(*static_cast<ControlReceived*>(event.get()));
                    break;
                case SerializableInfo::ActualMeasurement:
                    Orchestrator::get().emit(*static_cast<ActualMeasurement*>(event.get()));
                    break;
                case SerializableInfo::ActualControl:
                    Orchestrator::get().emit(*static_cast<ActualControl*>(event.get()));
                    break;
                case SerializableInfo::TimeUpdate:
                    Orchestrator::get().emit(*static_cast<TimeUpdate*>(event.get()));
                    break;
                case SerializableInfo::DynawoTimelineEvent:
                    Orchestrator::get().emit(*static_cast<DynawoTimelineEvent*>(event.get()));
                    break;
                case SerializableInfo::DynawoConstraintEvent:
                    Orchestrator::get().emit(*static_cast<DynawoConstraintEvent*>(event.get()));
                    break;
                case SerializableInfo::DumpStateEvent:
                    // Do not replay dump state event during replay
                    break;
                case SerializableInfo::RawDynawoCommand:
                    // Do not replay Dynawo commands during replay
                    break;
                case SerializableInfo::CycosimMeasurementReceived:
                case SerializableInfo::CycosimControlReceived:
                    // Do not replay Cycosim event during replay
                    break;
            }
        }
        buffer.clear();
    }

    setStep(step_index_ + 1);
    if (next_time_step_ <= target_time_) {
        Orchestrator::get().scheduleEvent(
            next_time_step_,
            makeCallback<&Replay::goToNextTimeStep>(this)
        );
    }
}

std::string Replay::getFullTableName(const std::string& table_name) const {
    return "`" + simulation_name_ + "`.`" + table_name + "`";
}

std::string Replay::generateQuery(int event_type, double start_time, double end_time) {
    std::ostringstream query;
    query << "SELECT * FROM " << getFullTableName(SERIALABLE_NAMES.at(event_type));

    auto type = static_cast<SerializableInfo>(event_type);
    switch (type) {
        case SerializableInfo::MeasurementSent:
        case SerializableInfo::ControlSent:
            query << " WHERE time_sent >= " << start_time << " AND time_sent < " << end_time;
            break;
        case SerializableInfo::MeasurementReceived:
        case SerializableInfo::ControlReceived:
        case SerializableInfo::CycosimMeasurementReceived:
        case SerializableInfo::CycosimControlReceived:
            query << " WHERE time_received >= " << start_time << " AND time_received < " << end_time;
            break;
        case SerializableInfo::ActualMeasurement:
        case SerializableInfo::ActualControl:
            query << " WHERE time >= " << start_time << " AND time < " << end_time;
            break;
        case SerializableInfo::TimeUpdate:
            query << " WHERE value >= " << start_time << " AND value < " << end_time;
            break;
        case SerializableInfo::DynawoTimelineEvent:
        case SerializableInfo::DynawoConstraintEvent:
        case SerializableInfo::DumpStateEvent:
        case SerializableInfo::RawDynawoCommand:
            query << " WHERE time >= " << start_time << " AND time < " << end_time;
            break;
        }

    if (!topic_filter_.empty()) {
        switch (type) {
            case SerializableInfo::MeasurementSent:
            case SerializableInfo::ControlSent:
            case SerializableInfo::MeasurementReceived:
            case SerializableInfo::ControlReceived:
            case SerializableInfo::ActualMeasurement:
            case SerializableInfo::ActualControl:
            case SerializableInfo::CycosimMeasurementReceived:
            case SerializableInfo::CycosimControlReceived:
                query << " AND topic='" << topic_filter_ << "'";
                break;
            case SerializableInfo::TimeUpdate:
            case SerializableInfo::DynawoTimelineEvent:
            case SerializableInfo::DynawoConstraintEvent:
            case SerializableInfo::DumpStateEvent:
            case SerializableInfo::RawDynawoCommand:
                // Event does not include a topic field, no never filtered by topic
                break;
        }
    }

    query << " FORMAT RowBinary";
    return query.str();
}

// This function will be called by libcurl to write the response into a buffer
size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t totalSize = size * nmemb;
    auto* buffer = static_cast<std::vector<char>*>(userp);
    buffer->insert(buffer->end(), static_cast<char*>(contents), static_cast<char*>(contents) + totalSize);
    return totalSize;
}

void Replay::fillBuffer(int event_type) {
    CURL* curl = curl_easy_init();
    if (!curl) throw std::runtime_error("CURL init failed");

    std::string query = generateQuery(event_type, current_time_, next_time_step_);

    std::vector<char> responseBuffer;
    curl_easy_setopt(curl, CURLOPT_URL, Credentials::get().getClickhouseURL());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, query.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, (long)strlen(query.c_str()));

    // Set write function and data buffer
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &responseBuffer);

    CURLcode res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);
    if (res != CURLE_OK)
        throw std::runtime_error("CURL failed: " + std::string(curl_easy_strerror(res)));

    // Deserialize
    ClickHouseBinaryReader reader(std::move(responseBuffer));
    auto type = static_cast<SerializableInfo>(event_type);

    while (reader.peek() != EOF) {
        switch (type) {
            case SerializableInfo::MeasurementSent:
                buffers_[event_type].emplace_back(MeasurementSent::deserialize(reader));
                break;
            case SerializableInfo::MeasurementReceived:
                buffers_[event_type].emplace_back(MeasurementReceived::deserialize(reader));
                break;
            case SerializableInfo::ControlSent:
                buffers_[event_type].emplace_back(ControlSent::deserialize(reader));
                break;
            case SerializableInfo::ControlReceived:
                buffers_[event_type].emplace_back(ControlReceived::deserialize(reader));
                break;
            case SerializableInfo::ActualMeasurement:
                buffers_[event_type].emplace_back(ActualMeasurement::deserialize(reader));
                break;
            case SerializableInfo::ActualControl:
                buffers_[event_type].emplace_back(ActualControl::deserialize(reader));
                break;
            case SerializableInfo::TimeUpdate:
                buffers_[event_type].emplace_back(TimeUpdate::deserialize(reader));
                break;
            case SerializableInfo::DynawoTimelineEvent:
                buffers_[event_type].emplace_back(DynawoTimelineEvent::deserialize(reader));
                break;
            case SerializableInfo::DynawoConstraintEvent:
                buffers_[event_type].emplace_back(DynawoConstraintEvent::deserialize(reader));
                break;
            case SerializableInfo::DumpStateEvent:
                // Do not replay dump state event during replay
                break;
            case SerializableInfo::RawDynawoCommand:
                // Do not replay Dynawo commands during replay
                break;
            case SerializableInfo::CycosimMeasurementReceived:
            case SerializableInfo::CycosimControlReceived:
                // Do not replay Cycosim event during replay
                break;
            }
        if (type == SerializableInfo::DumpStateEvent || type == SerializableInfo::RawDynawoCommand ||
            type == SerializableInfo::CycosimMeasurementReceived || type == SerializableInfo::CycosimControlReceived) {
            // Avoid infinite loop of reader.peek() != EOF since we don't actually deserialize those types of events
            break;
        }
    }
}

void Replay::fillBuffers() {
    // Pre-create all buffers in the main thread (std::unordered_map get on distinct keys is thread-safe, but not key insertion as it can trigger a rehash)
    for (const auto& [EVENT_TYPE, NAME] : SERIALABLE_NAMES) {
        buffers_[EVENT_TYPE];
    }

    std::vector<std::pair<int, std::future<void>>> jobs;
    for (const auto& [EVENT_TYPE, NAME] : SERIALABLE_NAMES) {
        // Each buffer is filled by one given thread from a thread pool
        jobs.emplace_back(EVENT_TYPE, pool_.enqueue([this, EVENT_TYPE]() {
            fillBuffer(EVENT_TYPE);
        }));
    }
    for (auto& [event_type, job] : jobs) {
        try {
            job.get();
        } catch (const std::exception& e) {
            throw std::runtime_error("Replay failed to fetch events of type " + SERIALABLE_NAMES.at(event_type) + ": " + e.what());
        }
    }
}
