/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DROP_FUNCTIONS_H
#define DROP_FUNCTIONS_H

#include "SerialisationHelper.h"

#include <random>

/**
 * Abstract class for drop functions. Any delay function is expected to have an apply(time_received) which returns 1 if the information is dropped, else 0
 */
class DropFunction {
    public:
        virtual ~DropFunction() = default;

        virtual bool apply(double time_received) = 0;

        /**
         * Returns true if the drop function makes the node/link that it is applied to unavailable
         */
        virtual bool makesUnavailable() = 0;

        template<class Archive>
        void serialize(Archive& ar) {
            ar();
        }
};
SER20_REGISTER_TYPE(DropFunction);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(DropFunction);

class FixedDrop: public DropFunction {
    public:
        FixedDrop(bool value):
            value_(value) {}
        FixedDrop() = default;  // Default constructor needed for deserialization

        bool apply(double time_received) override {
            (void) time_received;
            return value_;
        }

        bool makesUnavailable() override {
            return value_;
        }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DropFunction>(this), value_);
        }

    private:
        bool value_;
};
SER20_REGISTER_TYPE(FixedDrop);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(FixedDrop);

class RandomDrop: public DropFunction {
    public:
        RandomDrop(double drop_rate, size_t seed):
            drop_rate_(drop_rate),
            distrib_{0, 1},
            rng_(seed) {}
        RandomDrop() = default;  // Default constructor needed for deserialization

        bool apply(double time_received) override {
            (void) time_received;
            return drop_rate_ > distrib_(rng_);
        }

        bool makesUnavailable() override {
            return drop_rate_ >= 0.99;
        }

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<DropFunction>(this), drop_rate_, distrib_, rng_);
        }

    private:
        double drop_rate_;
        std::uniform_real_distribution<double> distrib_;
        std::mt19937 rng_;
};
SER20_REGISTER_TYPE(RandomDrop);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(RandomDrop);

enum class DropFunctions {
    FixedDrop,
    RandomDrop
};

[[maybe_unused]] static DropFunctions stringToDropFunction(const std::string& str) {
    if (str == "fixed") return DropFunctions::FixedDrop;
    if (str == "random") return DropFunctions::RandomDrop;
    throw std::invalid_argument("Unknown drop function type " + str);
}

#endif // DROP_FUNCTIONS_H
