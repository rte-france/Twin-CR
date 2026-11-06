/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DELAY_FUNCTIONS_H
#define DELAY_FUNCTIONS_H

#include "Information.h"
#include "SerialisationHelper.h"

#include <random>

/**
 * Abstract class for delay functions. Any delay function is expected to have an apply(info) method which modifies the time_received of an InformationReceived
 */
class DelayFunction {
    public:
        virtual ~DelayFunction() = default;

        virtual void apply(InformationReceived& info) = 0;

        template<class Archive>
        void serialize(Archive& ar) {
            ar();
        }
};
SER20_REGISTER_TYPE(DelayFunction);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(DelayFunction);

class FixedDelay: public DelayFunction {
    public:
        FixedDelay(double delay):
            delay_(delay) {}
        FixedDelay() = default;  // Default constructor needed for deserialization

        void apply(InformationReceived& info) override {
            info.time_received += delay_;
        }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DelayFunction>(this), delay_);
        }

    private:
        double delay_;
};
SER20_REGISTER_TYPE(FixedDelay);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(FixedDelay);

class GaussianDelay: public DelayFunction {
    public:
        GaussianDelay(double mean, double stddev, size_t seed):
            distrib_{mean, stddev},
            rng_(seed) {}
        GaussianDelay() = default;  // Default constructor needed for deserialization

        void apply(InformationReceived& info) override {
            info.time_received += distrib_(rng_);
        }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DelayFunction>(this), distrib_, rng_);
        }

    private:
        std::normal_distribution<double> distrib_;
        std::mt19937 rng_;
};
SER20_REGISTER_TYPE(GaussianDelay);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(GaussianDelay);

enum class DelayFunctions {
    FixedDelay,
    GaussianDelay
};

[[maybe_unused]] static DelayFunctions stringToDelayFunction(const std::string& str) {
    if (str == "fixed") return DelayFunctions::FixedDelay;
    if (str == "gauss") return DelayFunctions::GaussianDelay;
    throw std::invalid_argument("Unknown delay function type " + str);
}

#endif // DELAY_FUNCTIONS_H
