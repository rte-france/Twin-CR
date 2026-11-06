/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DYNAWO_EVENTS_H
#define DYNAWO_EVENTS_H

#include "DynawoSender.h"

#include <cmath>
#include <string>
#include <sstream>
#include <variant>
#include <unordered_map>
#include <vector>

using parameter_type = std::variant<bool, int, double>;

/**
 * Struct representing a Dynawo parameter
 */
struct Parameter {
    Parameter(std::string n, parameter_type v): name(n), value(v) {};
    std::string name;
    parameter_type value;

    static bool isPositive(parameter_type value) {
        if (std::holds_alternative<bool>(value))
            return std::get<bool>(value);
        else if (std::holds_alternative<int>(value))
            return std::get<int>(value) > 0;
        else
            return std::get<double>(value) >= 0.5;
    }

    static int toState(parameter_type value) {
        if (std::holds_alternative<bool>(value))
            return std::get<bool>(value) ? 1 : 2;  // True to open (1), false to close (2)
        else if (std::holds_alternative<int>(value))
            return std::get<int>(value) ;
        else
            return static_cast<int>(std::round(std::get<double>(value)));
    }

    operator std::string () const {
        std::stringstream ss;
        ss << name;
        if (std::holds_alternative<bool>(value))
            ss << "," << std::get<bool>(value);
        else if (std::holds_alternative<int>(value))
            ss << "," << std::get<int>(value);
        else
            ss << "," << std::get<double>(value);
        return ss.str();
        // {self.name},{self.type.name.lower()},{int(self.value)}"
    }
};

/**
 * Events that can be controlled from the DynawoInterface to impact the simulation in Dynawo
 */
class DynawoEvent {
    public:
        DynawoEvent(std::string name);
        virtual ~DynawoEvent() = default;

        /**
         * Reset the event. Needs to be done on some types of event (EventQuadripoleDisconnection, EventConnectedStatus, EventQuadripoleConnection,
         * EventSetPointBoolean, and EventSetPointReal) before they can re used again.
         */
        virtual void reset(DynawoSender& sender);

        /**
         * Launch event based on value
         */
        virtual void launchEvent(parameter_type value, DynawoSender& sender) = 0;

        operator std::string () const {
            std::stringstream ss;
            ss << name_;
            for (auto param: parameters_) {
                ss << "," << std::string(param.second);
            }
            return ss.str();
        };

        std::string name() const { return name_; }

    protected:
        void updateValue(std::string name, parameter_type value);

        std::string name_;
        std::unordered_map<std::string, Parameter> parameters_;
};

class EventQuadripoleDisconnection: public DynawoEvent {
    public:
        EventQuadripoleDisconnection(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;

    private:
        void open(DynawoSender& sender);

        void close(DynawoSender& sender);
};

class EventQuadripoleConnection: public DynawoEvent {
    public:
        EventQuadripoleConnection(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;

    private:
        void open(DynawoSender& sender);

        void close(DynawoSender& sender);
};

class EventConnectedStatus: public DynawoEvent {
    public:
        EventConnectedStatus(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;

    private:
        void open(DynawoSender& sender);

        void close(DynawoSender& sender);
};

class EventSetPointBoolean: public DynawoEvent {
    public:
        EventSetPointBoolean(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;
};

class EventSetPointReal: public DynawoEvent {
    public:
        EventSetPointReal(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;
};

class SetPoint: public DynawoEvent {
    public:
        SetPoint(std::string name);

        virtual void reset(DynawoSender&) override {};  // Setpoints don't need to be reset

        void launchEvent(parameter_type value, DynawoSender& sender) override;
};

class Updatable: public DynawoEvent {
    public:
        Updatable(std::string name): DynawoEvent(name) {};

        virtual void reset(DynawoSender&) override {};  // Updatables don't need to be reset
};

class UpdatableBoolean: public Updatable {
    public:
        UpdatableBoolean(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;
};

class UpdatableInteger: public Updatable {
    public:
        UpdatableInteger(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;
};

class UpdatableDiscrete: public Updatable {
    public:
        UpdatableDiscrete(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;

        void scaleMultiplierBy(double relative_change, DynawoSender& sender);

    private:
        double multiplier_ = 1;
};

class UpdatableContinuous: public Updatable {
    public:
        UpdatableContinuous(std::string name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;

        void scaleMultiplierBy(double relative_change, DynawoSender& sender);

    private:
        double multiplier_ = 1;
};

class ModelParameters: public DynawoEvent {
    public:
        ModelParameters(std::string name): DynawoEvent(name) {};

        void addParameter(std::string parameter_name);

        void launchEvent(parameter_type value, DynawoSender& sender) override;

        void launchEvent(std::string parameter_name, parameter_type value, DynawoSender& sender);

        void reset(DynawoSender& sender) override { (void) sender; };

    private:
        std::vector<std::string> parameter_names_;  // Configured parameters, parameters_ only holds the ones already set
};

enum class DynawoEventClasses {
    EventQuadripoleDisconnection,
    EventConnectedStatus,
    EventQuadripoleConnection,
    EventSetPointBoolean,
    EventSetPointReal,
    SetPoint,
    UpdatableBoolean,
    UpdatableInteger,
    UpdatableDiscrete,
    UpdatableContinuous
};

[[maybe_unused]] static DynawoEventClasses stringToDynawoEventClass(const std::string& str) {
    if (str == "EventQuadripoleDisconnection") return DynawoEventClasses::EventQuadripoleDisconnection;
    if (str == "EventConnectedStatus")  return DynawoEventClasses::EventConnectedStatus;
    if (str == "EventQuadripoleConnection")  return DynawoEventClasses::EventQuadripoleConnection;
    if (str == "EventSetPointBoolean")  return DynawoEventClasses::EventSetPointBoolean;
    if (str == "EventSetPointReal")  return DynawoEventClasses::EventSetPointReal;
    if (str == "SetPoint")  return DynawoEventClasses::SetPoint;
    if (str == "DYNModelUpdatableBoolean")  return DynawoEventClasses::UpdatableBoolean;
    if (str == "DYNModelUpdatableInteger")  return DynawoEventClasses::UpdatableInteger;
    if (str == "DYNModelUpdatableDiscrete")  return DynawoEventClasses::UpdatableDiscrete;
    if (str == "DYNModelUpdatableContinuous")  return DynawoEventClasses::UpdatableContinuous;
    throw std::runtime_error("Unknown Dynawo event type: " + str);
}

#endif // DYNAWO_EVENTS_H
