/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DynawoEvents.h"

#include <spdlog/spdlog.h>

#include <algorithm>


DynawoEvent::DynawoEvent(std::string name):
name_(name),
parameters_({}) {};

void DynawoEvent::updateValue(std::string name, parameter_type value) {
    if (!parameters_.contains(name)) {
        spdlog::warn("DynawoEvent parameter {} does not exist for event {}", name, name_);
    } else {
        parameters_.at(name).value = value;
    }
}

void DynawoEvent::reset(DynawoSender& sender) {
    parameters_.at("event_tEvent").value = 1000000.0;
    sender.sendAction(std::string(*this));
}

EventQuadripoleDisconnection::EventQuadripoleDisconnection(std::string name) :
DynawoEvent(name) {
    parameters_.emplace("event_tEvent", Parameter("event_tEvent", 0.0));
    parameters_.emplace("event_disconnectExtremity", Parameter("event_disconnectExtremity", false));
    parameters_.emplace("event_disconnectOrigin", Parameter("event_disconnectOrigin", false));
};

void EventQuadripoleDisconnection::open(DynawoSender& sender) {
    parameters_.at("event_tEvent").value = 0.0;
    parameters_.at("event_disconnectExtremity").value = true;
    parameters_.at("event_disconnectOrigin").value = true;
    sender.sendAction(std::string(*this));
}

void EventQuadripoleDisconnection::close(DynawoSender& sender) {
    parameters_.at("event_tEvent").value = 0.0;
    parameters_.at("event_disconnectExtremity").value = false;
    parameters_.at("event_disconnectOrigin").value = false;
    sender.sendAction(std::string(*this));
}

void EventQuadripoleDisconnection::launchEvent(parameter_type value, DynawoSender& sender) {
    if (Parameter::isPositive(value)) {
        open(sender);
        spdlog::debug("Opening line {}", name_);
    }
    else {
        close(sender);
        spdlog::debug("Closing line {}", name_);
    }
}

EventQuadripoleConnection::EventQuadripoleConnection(std::string name) :
DynawoEvent(name) {
    parameters_.emplace("event_tEvent", Parameter("event_tEvent", 0.0));
    parameters_.emplace("event_connectExtremity", Parameter("event_connectExtremity", false));
    parameters_.emplace("event_connectOrigin", Parameter("event_connectOrigin", false));
};

void EventQuadripoleConnection::open(DynawoSender& sender) {
    parameters_.at("event_tEvent").value = 0.0;
    parameters_.at("event_connectExtremity").value = false;
    parameters_.at("event_connectOrigin").value = false;
    sender.sendAction(std::string(*this));
}

void EventQuadripoleConnection::close(DynawoSender& sender) {
    parameters_.at("event_tEvent").value = 0.0;
    parameters_.at("event_connectExtremity").value = true;
    parameters_.at("event_connectOrigin").value = true;
    sender.sendAction(std::string(*this));
}

void EventQuadripoleConnection::launchEvent(parameter_type value, DynawoSender& sender) {
    if (Parameter::isPositive(value)) {
        close(sender);
        spdlog::debug("Connecting line {}", name_);
    }
    else {
        open(sender);
        spdlog::debug("Disconnecting line {}", name_);
    }
}

EventConnectedStatus::EventConnectedStatus(std::string name) :
DynawoEvent(name) {
    parameters_.emplace("event_tEvent", Parameter("event_tEvent", 0.0));
    parameters_.emplace("event_open", Parameter("event_open", false));
};

void EventConnectedStatus::open(DynawoSender& sender) {
    parameters_.at("event_tEvent").value = 0.0;
    parameters_.at("event_open").value = true;
    sender.sendAction(std::string(*this));
}

void EventConnectedStatus::close(DynawoSender& sender) {
    parameters_.at("event_tEvent").value = 0.0;
    parameters_.at("event_open").value = false;
    sender.sendAction(std::string(*this));
}

void EventConnectedStatus::launchEvent(parameter_type value, DynawoSender& sender) {
    if (Parameter::isPositive(value)) {
        open(sender);
        spdlog::debug("Opening line {}", name_);
    }
    else {
        close(sender);
        spdlog::debug("Closing line {}", name_);
    }
}

EventSetPointBoolean::EventSetPointBoolean(std::string name) :
DynawoEvent(name) {
    parameters_.emplace("event_tEvent", Parameter("event_tEvent", 0.0));
    parameters_.emplace("event_stateEvent1", Parameter("event_stateEvent1", true));
};

void EventSetPointBoolean::launchEvent(parameter_type value, DynawoSender& sender) {
    updateValue("event_tEvent", 0.0);
    updateValue("event_stateEvent1", Parameter::isPositive(value));
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

EventSetPointReal::EventSetPointReal(std::string name) :
DynawoEvent(name) {
    parameters_.emplace("event_tEvent", Parameter("event_tEvent", 0.0));
    parameters_.emplace("event_stateEvent1", Parameter("event_stateEvent1", 0));
};

void EventSetPointReal::launchEvent(parameter_type value, DynawoSender& sender) {
    updateValue("event_tEvent", 0.0);
    updateValue("event_stateEvent1", value);
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

SetPoint::SetPoint(std::string name) :
DynawoEvent(name) {
    parameters_.emplace("setPoint_Value0", Parameter("setPoint_Value0", 0));
};

void SetPoint::launchEvent(parameter_type value, DynawoSender& sender) {
    updateValue("setPoint_Value0", value);
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

UpdatableBoolean::UpdatableBoolean(std::string name) :
Updatable(name) {
    parameters_.emplace("input_value", Parameter("input_value", false));
};

void UpdatableBoolean::launchEvent(parameter_type value, DynawoSender& sender) {
    updateValue("input_value", Parameter::isPositive(value));
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

UpdatableInteger::UpdatableInteger(std::string name) :
Updatable(name) {
    parameters_.emplace("input_value", Parameter("input_value", 0));
};

void UpdatableInteger::launchEvent(parameter_type value, DynawoSender& sender) {
    updateValue("input_value", Parameter::toState(value));
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

UpdatableDiscrete::UpdatableDiscrete(std::string name) :
Updatable(name) {
    parameters_.emplace("input_value", Parameter("input_value", 0.0));
};

void UpdatableDiscrete::launchEvent(parameter_type value, DynawoSender& sender) {
    multiplier_ = 1;  // Changing the input_value always reset the multiplier to 1 (in Dynawo)
    parameters_.erase("input_multiplier");  // Only send the multiplier when scaling
    parameters_.insert_or_assign("input_value", Parameter("input_value", value));
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

void UpdatableDiscrete::scaleMultiplierBy(double relative_change, DynawoSender& sender) {
    multiplier_ *= (1.0 + relative_change);
    parameters_.erase("input_value");  // input_multiplier is not read if input_value is specified
    // updateValue("input_multiplier", multiplier_);
    parameters_.insert_or_assign("input_multiplier", Parameter("input_multiplier", 1.0 + relative_change));

    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

UpdatableContinuous::UpdatableContinuous(std::string name) :
Updatable(name) {
    parameters_.emplace("input_value", Parameter("input_value", 0.0));
};

void UpdatableContinuous::launchEvent(parameter_type value, DynawoSender& sender) {
    multiplier_ = 1;  // Changing the input_value always reset the multiplier to 1 (in Dynawo)
    parameters_.erase("input_multiplier");  // Only send the multiplier when scaling
    parameters_.insert_or_assign("input_value", Parameter("input_value", value));
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}

void UpdatableContinuous::scaleMultiplierBy(double relative_change, DynawoSender& sender) {
    multiplier_ *= (1.0 + relative_change);
    parameters_.erase("input_value");  // input_multiplier is not read if input_value is specified
    // updateValue("input_multiplier", multiplier_);
    parameters_.insert_or_assign("input_multiplier", Parameter("input_multiplier", 1.0 + relative_change));

    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}


void ModelParameters::addParameter(std::string parameter_name) {
    if (std::find(parameter_names_.begin(), parameter_names_.end(), parameter_name) == parameter_names_.end())
        parameter_names_.push_back(parameter_name);
}

void ModelParameters::launchEvent(parameter_type value, DynawoSender& sender) {
    if (parameter_names_.empty()) {
        spdlog::warn("ModelParameters {} has no parameters, cannot launch event", name_);
        return;
    }
    // Default to the first parameter if only value is provided
    launchEvent(parameter_names_.front(), value, sender);
}

void ModelParameters::launchEvent(std::string parameter_name, parameter_type value, DynawoSender& sender) {
    if (std::find(parameter_names_.begin(), parameter_names_.end(), parameter_name) == parameter_names_.end()) {
        spdlog::warn("DynawoEvent parameter {} does not exist for event {}", parameter_name, name_);
        return;
    }

    parameters_.insert_or_assign(parameter_name, Parameter(parameter_name, value));
    std::string event_string = std::string(*this);
    spdlog::debug("Launching event {}", event_string);
    sender.sendAction(event_string);
}
