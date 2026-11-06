/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef INFORMATION_H
#define INFORMATION_H

#include "Serialization.h"
#include "Tase2.h"

#include <iostream>
#include <memory>
#include <optional>
#include <ostream>
#include <stdexcept>
#include <unordered_map>
#include <vector>
#include <string>
#include <sstream>
#include <cstring>
#include <cstddef>

#include <graaflib/graph.h>
#include <nlohmann/json.hpp>

enum class SerializableInfo {
    MeasurementSent = 0,
    MeasurementReceived = 1,
    ControlSent = 2,
    ControlReceived = 3,
    ActualMeasurement = 4,
    ActualControl = 5,
    TimeUpdate = 6,
    DynawoTimelineEvent = 7,
    DynawoConstraintEvent = 8,
    DumpStateEvent = 9,
    CycosimMeasurementReceived = 10,
    CycosimControlReceived = 11,
    RawDynawoCommand = 12,
};

const std::unordered_map<int, std::string> SERIALABLE_NAMES = {
    {0, "MeasurementSent"},
    {1, "MeasurementReceived"},
    {2, "ControlSent"},
    {3, "ControlReceived"},
    {4, "ActualMeasurement"},
    {5, "ActualControl"},
    {6, "TimeUpdate"},
    {7, "DynawoTimelineEvent"},
    {8, "DynawoConstraintEvent"},
    {9, "DumpStateEvent"},
    {10, "CycosimMeasurementReceived"},
    {11, "CycosimControlReceived"},
    {12, "RawDynawoCommand"},
};

struct Serializable {
    virtual ~Serializable() = default;
    virtual void serialize(ClickHouseBinaryBuffer& buf) const = 0;
    virtual constexpr int getType() const = 0;
    virtual double getTime() const = 0;
};

/**
 * Information object, handled by the Information flow model
 */
struct Information : public Serializable {
    Information(const std::string& id_, const Value& value_, double time_sent_, const std::string& destination_, const std::vector<graaf::vertex_id_t>& path_, const std::string& topic_, std::optional<tase2::Tase2Extension> tase2_data_)
        : id(id_), value(value_), time_sent(time_sent_), destination(destination_), path(path_), topic(topic_), tase2_data(std::move(tase2_data_)) {}

    std::string id;
    Value value;
    double time_sent;
    std::string destination;
    std::vector<graaf::vertex_id_t> path;
    std::string topic;
    std::optional<tase2::Tase2Extension> tase2_data;

    virtual operator std::string () const = 0;
};

struct MeasurementSent : public Information {
    MeasurementSent(const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::vector<graaf::vertex_id_t>& path, const std::string& topic, std::optional<tase2::Tase2Extension> tase2_data)
        : Information(id, value, time_sent, destination, path, topic, std::move(tase2_data)) {};

    operator std::string () const override {
        std::stringstream ss;
        ss << "MeasurementSent" << ", " << id << ", " << value << ", " << time_sent;
        for (auto it : path) {
            ss << ", " << it;
        }
        return ss.str();
    }

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::MeasurementSent);
    }

    double getTime() const override { return time_sent; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, id, value, time_sent, destination, topic, tase2_data);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        std::string id;
        Value value;
        double time_sent;
        std::string destination;
        std::vector<graaf::vertex_id_t> path = {};  // path is not serialized
        std::string topic;
        std::optional<tase2::Tase2Extension> tase2_data;
        reader.deserialize(id, value, time_sent, destination, topic, tase2_data);
        return std::make_unique<MeasurementSent>(id, value, time_sent, destination, path, topic, tase2_data);
    }
};

struct ControlSent : public Information {
    ControlSent(const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::vector<graaf::vertex_id_t>& path, const std::string& topic, std::optional<tase2::Tase2Extension> tase2_data)
        : Information(id, value, time_sent, destination, path, topic, std::move(tase2_data)) {};

    operator std::string () const override {
        std::stringstream ss;
        ss << "ControlSent" << ", " << id << ", " << value << ", " << time_sent;
        for (auto it : path) {
            ss << ", " << it;
        }
        return ss.str();
    }

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::ControlSent);
    }

    double getTime() const override { return time_sent; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, id, value, time_sent, destination, topic, tase2_data);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        std::string id;
        Value value;
        double time_sent;
        std::string destination;
        std::vector<graaf::vertex_id_t> path = {};  // path is not serialized
        std::string topic;
        std::optional<tase2::Tase2Extension> tase2_data;
        reader.deserialize(id, value, time_sent, destination, topic, tase2_data);
        return std::make_unique<ControlSent>(id, value, time_sent, destination, path, topic, tase2_data);
    }
};

struct InformationReceived : public Information {
    InformationReceived(const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::vector<graaf::vertex_id_t>& path, const std::string& topic, std::optional<tase2::Tase2Extension> tase2_data, double time_received_)
        : Information(id, value, time_sent, destination, path, topic, std::move(tase2_data)), time_received(time_received_) {};
    double time_received;
};

class Replay;

struct MeasurementReceived : public InformationReceived {
    // Constructor to initialize from a MeasurementSent
    MeasurementReceived(const MeasurementSent& measure, double time_received)
        : InformationReceived(measure.id, measure.value, measure.time_sent, measure.destination, measure.path, measure.topic, std::move(measure.tase2_data), time_received) {}

    operator std::string () const override {
        std::stringstream ss;
        ss << "MeasurementReceived" << ", " << id << ", " << value << ", " << time_sent << ", " << time_received;
        for (auto it : path) {
            ss << ", " << it;
        }
        return ss.str();
    }

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::MeasurementReceived);
    }

    double getTime() const override { return time_received; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, id, value, time_sent, destination, topic, tase2_data, time_received);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        std::string id;
        Value value;
        double time_sent;
        std::string destination;
        std::string topic;
        std::optional<tase2::Tase2Extension> tase2_data;
        double time_received;
        reader.deserialize(id, value, time_sent, destination, topic, tase2_data, time_received);
        auto event = MeasurementReceived(id, value, time_sent, destination, topic, std::move(tase2_data), time_received);
        return std::make_unique<MeasurementReceived>(event);
    }

    private:
        // Contructor to initialize directly (bypasses information flow model, meant to be used by the replayer)
        MeasurementReceived(const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::string& topic, std::optional<tase2::Tase2Extension> tase2_data, double time_received)
            : InformationReceived(id, value, time_sent, destination, {}, topic, tase2_data, time_received) {}
        friend Replay;
};

struct CycosimMeasurementReceived : public MeasurementReceived {
    CycosimMeasurementReceived(const std::string& source_, const MeasurementReceived& measure)
        : MeasurementReceived(measure), source(source_) {}

    std::string source;  // Where the measurement has become a CycosimMeasurement

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::CycosimMeasurementReceived);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        (void) reader;
        throw std::runtime_error("Not implemented (Cycosim events not meant to be replayed)");
    }
};

class ScenarioHandler;

struct ControlReceived : public InformationReceived {
    // Constructor to initialize from ControlSent
    ControlReceived(const ControlSent& control, double time_received)
        : InformationReceived(control.id, control.value, control.time_sent, control.destination, control.path, control.topic, control.tase2_data, time_received) {}

    operator std::string () const override {
        std::stringstream ss;
        ss << "ControlReceived" << ", " << id << ", " << value << ", " << time_sent << ", " << time_received;
        for (auto it : path) {
            ss << ", " << it;
        }
        return ss.str();
    }

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::ControlReceived);
    }

    double getTime() const override { return time_received; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, id, value, time_sent, destination, topic, tase2_data, time_received);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        std::string id;
        Value value;
        double time_sent;
        std::string destination;
        std::string topic;
        std::optional<tase2::Tase2Extension> tase2_data;
        double time_received;
        reader.deserialize(id, value, time_sent, destination, topic, tase2_data, time_received);
        auto event = ControlReceived(id, value, time_sent, destination, topic, tase2_data, time_received);
        return std::make_unique<ControlReceived>(event);
    }

    private:
        // Contructor to initialize directly (bypasses information flow model, to be used only in some scenarios)
        ControlReceived(const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::string& topic, std::optional<tase2::Tase2Extension> tase2_data)
            : InformationReceived(id, value, time_sent, destination, {}, topic, tase2_data, time_sent) {}
        friend ScenarioHandler;

        // Contructor to initialize directly (bypasses information flow model, meant to be used by the replayer (deserialisation))
        ControlReceived(const std::string& id, const Value& value, double time_sent, const std::string& destination, const std::string& topic, std::optional<tase2::Tase2Extension> tase2_data, double time_received)
        : InformationReceived(id, value, time_sent, destination, {}, topic, tase2_data, time_received) {}
        friend Replay;
};

struct CycosimControlReceived : public ControlReceived {
    CycosimControlReceived(const std::string& source_, const ControlReceived& measure)
        : ControlReceived(measure), source(source_) {}

    std::string source;  // Where the measurement has become a CycosimMeasurement

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::CycosimControlReceived);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        (void) reader;
        throw std::runtime_error("Not implemented (Cycosim events not meant to be replayed)");
    }
};

/**
 * Value object, bypasses the information flow model, and is typically sent to the Game Master (e.g. to State view without any delay nor data corruption)
 */
struct ActualValue : public Serializable {
    ActualValue(const std::string& id_, const Value& value_, double time_, const std::string& topic_)
        : id(id_), value(value_), time(time_), topic(topic_) {}

    std::string id;
    Value value;
    double time;
    std::string topic;
};

struct ActualMeasurement : public ActualValue {
    ActualMeasurement(const std::string& id, const Value& value, double time, const std::string& topic)
        : ActualValue(id, value, time, topic) {}

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::ActualMeasurement);
    }

    double getTime() const override { return time; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, id, value, time, topic);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        std::string id;
        Value value;
        double time;
        std::string topic;
        reader.deserialize(id, value, time, topic);
        return std::make_unique<ActualMeasurement>(id, value, time, topic);
    }
};

struct ActualControl : public ActualValue {
    ActualControl(const std::string& id, const Value& value, double time, const std::string& topic)
        : ActualValue(id, value, time, topic) {}

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::ActualControl);
    }

    double getTime() const override { return time; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, id, value, time, topic);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        std::string id;
        Value value;
        double time;
        std::string topic;
        reader.deserialize(id, value, time, topic);
        return std::make_unique<ActualControl>(id, value, time, topic);
    }
};

struct TimeUpdate : public Serializable {
    TimeUpdate(double value_) : value(value_) {}

    double value;

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::TimeUpdate);
    }

    double getTime() const override { return value; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, value);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        double value;
        reader.deserialize(value);
        return std::make_unique<TimeUpdate>(value);
    }
};

struct DynawoTimelineEvent : Serializable {
    DynawoTimelineEvent(std::string event_string_) : event_string(event_string_) {
        try {
            auto j = nlohmann::json::parse(event_string_);
            try {
                time = j["time"];
            } catch (nlohmann::detail::type_error const&) {
                time = std::stod(j["time"].get<std::string>());  // Time is given as string instead of double
            }
            model_name = j["modelName"];
            message = j["message"];
        } catch (const nlohmann::detail::type_error& e) {
            throw std::runtime_error("Failed to read DynawoTimelineEvent: " + std::string(e.what()) + " in:\n" + event_string);
        }
    }

    double time;
    std::string model_name;
    std::string message;

    std::string event_string;

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::DynawoTimelineEvent);
    }

    double getTime() const override { return time; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, time, model_name, message);
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        double time;
        std::string model_name;
        std::string message;
        reader.deserialize(time, model_name, message);
        nlohmann::json j = {
            {"time", time},
            {"modelName", model_name},
            {"message", message}
        };
        std::string event_string = j.dump();
        return std::make_unique<DynawoTimelineEvent>(event_string);
    }
};

struct DynawoConstraintEvent : public Serializable {
    DynawoConstraintEvent(std::string event_string_) : event_string(event_string_) {
        try {
            auto j = nlohmann::json::parse(event_string_);
            description = j["description"];
            model_name = j["modelName"];
            try {
                time = j["time"];
            } catch (nlohmann::detail::type_error const&) {
                time = std::stod(j["time"].get<std::string>());  // Time is given as string instead of double
            }
            type = j["eventType"];
        } catch (const nlohmann::detail::type_error& e) {
            throw std::runtime_error("Failed to read DynawoConstraintEvent: " + std::string(e.what()) + " in:\n" + event_string);
        }
    }

    std::string description;
    std::string model_name;
    double time;
    std::string type;

    std::string event_string;

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::DynawoConstraintEvent);
    }

    double getTime() const override { return time; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, description, model_name, time, type, event_string);
        // Event string is also serialised as it contains other (optional) fields other than description, modelName, time, and type
    }

    static std::unique_ptr<Serializable> deserialize(ClickHouseBinaryReader& reader) {
        std::string description;
        std::string model_name;
        double time;
        std::string type;
        std::string event_string;
        reader.deserialize(description, model_name, time, type, event_string);
        (void) description;
        (void) model_name;
        (void) time;
        (void) type;
        return std::make_unique<DynawoConstraintEvent>(event_string);
    }
};

struct DumpStateEvent : public Serializable {
    DumpStateEvent(double time_)
        : time(time_) {}

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::DumpStateEvent);
    }

    double getTime() const override { return time; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        ::serialize(buf, time);
    }

    double time;
};

struct RawDynawoCommand : public Serializable {
    RawDynawoCommand(const std::string& command_, int zmq_flag_, uint64_t event_count_, double time_)
        : command(command_), zmq_flag(zmq_flag_), event_count(event_count_), time(time_) {}

    int constexpr getType() const override {
        return static_cast<int>(SerializableInfo::RawDynawoCommand);
    }

    double getTime() const override { return time; }

    void serialize(ClickHouseBinaryBuffer& buf) const override {
        static_assert(sizeof(int) == 4, "int must be 32-bit for ClickHouse Int32 mapping");
        ::serialize(buf, command, zmq_flag, event_count, time);
    }

    std::string command;
    int zmq_flag;
    uint64_t event_count;
    double time;
};

#endif // INFORMATION_H
