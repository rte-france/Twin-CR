/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "CommunicationElements.h"
#include "DelayFunctions.h"
#include "DropFunctions.h"
#include "NetworkGraph.h"
#include "Orchestrator.h"
#include "../utils/JsonExtension.h"
#include <cstdlib>
#include <memory>

bool CommunicationElement::apply(MeasurementReceived& info) {
    return genericApply(info);
}

bool CommunicationElement::apply(ControlReceived& info) {
    return genericApply(info);
}

bool CommunicationElement::apply(AcknowledgementReceived& info) {
    return genericApply(info);
}

void CommunicationElement::setDelayFunction(const nlohmann::json::basic_json::value_type& config, Mode mode) {
    if (config.empty()) {
        delay_function_.reset();
        delay_function_config_ = {};
        return;
    }

    try {
        std::string delay_type = config["type"];

        switch (stringToDelayFunction(delay_type)) {
            case DelayFunctions::FixedDelay: {
                double delay = config["delay"];
                if (mode == Mode::Execute)
                    delay_function_ = std::make_shared<FixedDelay>(delay);
                break;
            }
            case DelayFunctions::GaussianDelay: {
                double mean = get_or_default(config, {"mean"}, 1.0);
                double stddev = get_or_default(config, {"stddev"}, 1.0);
                if (mode == Mode::Execute)
                    delay_function_ = std::make_shared<GaussianDelay>(mean, stddev, seed_ + 1);
                break;
            }
        }
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid config: " + std::string(e.what()) + " in:\n" + config.dump());
    }

    if (mode == Mode::Execute) {
        delay_function_config_ = config;
    }
}

void CommunicationElement::setDropFunction(const nlohmann::json::basic_json::value_type& config, Mode mode) {
    if (config.empty()) {
        drop_function_.reset();
        drop_function_config_ = {};
        return;
    }

    try {
        std::string drop_type = config["type"];

        switch (stringToDropFunction(drop_type)) {
            case DropFunctions::FixedDrop: {
                bool value = config["value"];
                if (mode == Mode::Execute) {
                    drop_function_ = std::make_shared<FixedDrop>(value);
                    setAvailable(!(*drop_function_)->makesUnavailable());
                }
                break;
            }
            case DropFunctions::RandomDrop: {
                double drop_rate = config["value"];
                if (mode == Mode::Execute) {
                    drop_function_ = std::make_shared<RandomDrop>(drop_rate, seed_ + 2);
                    setAvailable(!(*drop_function_)->makesUnavailable());
                }
                break;
            }
        }
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid config: " + std::string(e.what()) + " in:\n" + config.dump());
    }

    if (mode == Mode::Execute) {
        drop_function_config_ = config;
    }
}

void CommunicationElement::addCorruptionFunction(const nlohmann::json::basic_json::value_type& config, Mode mode) {
    if (config.empty())
        return;
    try {
        std::string corruption_type = config["type"];
        double corruption_likelihood = get_or_default(config, {"likelihood"}, 1.0);
        size_t seed = seed_ + 3 + corruption_functions_.size();

        switch (stringToCorruptionFunction(corruption_type)) {
            case CorruptionFunctions::NoCorruption:
                if (mode == Mode::Execute)
                    corruption_functions_.push_back(std::make_shared<NoCorruption>(seed, corruption_likelihood));
                break;

            case CorruptionFunctions::RandomNoiseMeasurementCorruption: {
                double noise_min = get_or_throw<double>(config, {"noise_min"});
                double noise_max = get_or_throw<double>(config, {"noise_max"});
                std::pair<double, double> noise_range = {noise_min, noise_max};

                if (mode == Mode::Execute)
                    corruption_functions_.push_back(std::make_shared<RandomNoiseMeasurementCorruption>(seed, corruption_likelihood, noise_range));
                break;
            }
            case CorruptionFunctions::RandomNoiseControlCorruption: {
                double noise_min = get_or_throw<double>(config, {"noise_min"});
                double noise_max = get_or_throw<double>(config, {"noise_max"});
                std::pair<double, double> noise_range = {noise_min, noise_max};

                if (mode == Mode::Execute)
                    corruption_functions_.push_back(std::make_shared<RandomNoiseControlCorruption>(seed, corruption_likelihood, noise_range));
                break;
            }
            case CorruptionFunctions::ZeroOutMeasurementCorruption: {
                double zero_value = get_or_default(config, {"zero_value"}, 0);

                if (mode == Mode::Execute)
                    corruption_functions_.push_back(std::make_shared<ZeroOutMeasurementCorruption>(seed, corruption_likelihood, zero_value));
                break;
            }
            case CorruptionFunctions::ShiftMeasurementCorruption: {
                double shift_value = get_or_default(config, {"shift_value"}, 0);

                if (mode == Mode::Execute)
                    corruption_functions_.push_back(std::make_shared<ShiftMeasurementCorruption>(seed, corruption_likelihood, shift_value));
                break;
            }
            case CorruptionFunctions::InvertControlCorruption: {
                double invert_factor = get_or_default(config, {"invert_factor"}, -1);

                if (mode == Mode::Execute)
                    corruption_functions_.push_back(std::make_shared<InvertControlCorruption>(seed, corruption_likelihood, invert_factor));
                break;
            }
            default:
                throw;
        }
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid config: " + std::string(e.what()) + " in:\n" + config.dump());
    }

    if (mode == Mode::Execute) {
        corruption_function_configs_.emplace_back(config);
    }
}

void CommunicationElement::clearCorruptionFunctions(Mode mode) {
    if (mode == Mode::Execute) {
        corruption_functions_.clear();
        corruption_function_configs_.clear();
    }
}

void CommunicationElement::setAvailable(bool available) {
    if (available_ != available) {
        available_ = available;
        notifyObservers();
    }
}

void CommunicationElement::notifyObservers() {
    for (auto& observer : observers_) {
        observer->onElementAvailabilityChanged();
    }
}

MonitoredPath::MonitoredPath(const std::string& source, const std::string& destination, NetworkGraph& network_graph) :
destination_(destination),
path_(network_graph.getPath(source, destination)),
available_(true),
network_graph_(&network_graph) {
    //
}

void MonitoredPath::init(NetworkGraph& network_graph) {
    graaf::vertex_id_t sender;
    graaf::vertex_id_t receiver;

    if (path_.size() < 2) {
        throw std::runtime_error("The source and destination of a MonitoredPath should be different");
    }
    auto it = path_.begin();
    sender = *it;
    it++;
    do {
        receiver = *it;

        auto node = network_graph.getNodePtr(sender);
        elements_.emplace_back(node);
        node->addObserver(shared_from_this());

        auto link = network_graph.getLinkPtr(sender, receiver);
        elements_.emplace_back(link);
        link->addObserver(shared_from_this());

        // Also monitors the reverse path (like a ping test)
        auto reverse_link = network_graph.getLinkPtr(receiver, sender);
        elements_.emplace_back(reverse_link);
        reverse_link->addObserver(shared_from_this());

        sender = *it;
        it++;
    } while (it != path_.end());

    auto node = network_graph.getNodePtr(receiver);
    elements_.emplace_back(node);
    node->addObserver(shared_from_this());

    updateAvailability();
}

void MonitoredPath::updateAvailability() {
    bool all_available = true;
    for (auto element : elements_) {
        if (!element->isAvailable()) {
            all_available = false;
            break;
        }
    }

    if (!available_ && all_available) {  // Send CG when path becomes available (and was unavailable before)
        Orchestrator::get().emit(ControlSent("CG", 0, Orchestrator::get().getCurrentTime(), destination_, path_, "CG",
            tase2::Tase2Extension(
                "CG",
                tase2::SignalisationType::CG,
                tase2::CAUSE_SPONTANEOUS,
                tase2::QUALITY_VALIDITY_GOOD,
                false
            ),
            network_graph_->nextControlUid()));
    }
    available_ = all_available;
}
