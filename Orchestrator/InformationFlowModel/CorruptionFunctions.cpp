/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "CorruptionFunctions.h"

bool CorruptionFunction::likely() {
    std::uniform_real_distribution<> uniform(0, 1);
    return uniform(random_generator_) < likelihood_;
}

void RandomNoiseMeasurementCorruption::apply(MeasurementReceived &info) {
    if (likely()) {
        std::uniform_real_distribution<> distrib(noise_range_.first, noise_range_.second);
        // Cast the info.value to double, add the noise, then convert back to initial type
        double new_value = info.value.to_double() + distrib(random_generator_);
        info.value.update(new_value);
    }
}

void RandomNoiseControlCorruption::apply(ControlReceived &info) {
    if (likely()) {
        std::uniform_real_distribution<> distrib(noise_range_.first, noise_range_.second);
        // Cast the info.value to double, add the noise, then convert back to initial type
        double new_value = info.value.to_double() + distrib(random_generator_);
        info.value.update(new_value);
    }
}

void ZeroOutMeasurementCorruption::apply(MeasurementReceived &info) {
    if (likely()) {
        info.value.update(zero_value_);
    }
}

void ShiftMeasurementCorruption::apply(MeasurementReceived &info) {
    if (likely()) {
        // Cast the info.value to double, add the noise, then convert back to initial type
        double new_value = info.value.to_double() + shift_value_;
        info.value.update(new_value);
    }
}

void InvertControlCorruption::apply(ControlReceived &info) {
    if (likely()) {
        // Cast the info.value to double, add the noise, then convert back to initial type
        double new_value = info.value.to_double() * invert_factor_;
        info.value.update(new_value);
    }
}
