/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef CORRUPTION_FUNCTIONS_H
#define CORRUPTION_FUNCTIONS_H

#include "Information.h"
#include "SerialisationHelper.h"

#include <random>

/**
 * Abstract class for corruption functions. Any corruption function must have:
 * (i) a likelihood (i.e. how likely is it that the function is called when an information is received)
 * (ii) a function that acts on MeasurementReceived and/or ControlReceived events (i.e. when a CommunicationElement.apply() function is called)
 */
class CorruptionFunction {
    public:
        CorruptionFunction(size_t seed, double likelihood):
            random_generator_(seed),
            likelihood_(likelihood) {}
        virtual ~CorruptionFunction() = default;
        CorruptionFunction() = default;  // Default constructor needed for deserialization

        bool likely();

        virtual void apply(MeasurementReceived& info) = 0;
        virtual void apply(ControlReceived& info) = 0;

        template<class Archive>
        void serialize(Archive& ar) {
            ar(random_generator_, likelihood_);
        }

    protected:
        std::mt19937 random_generator_;
        double likelihood_;
};
SER20_REGISTER_TYPE(CorruptionFunction);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(CorruptionFunction);

/**
 * Abstract class for corruption functions that only apply to MeasurementReeceived events
 */
class MeasurementCorruptionFunction: public CorruptionFunction {
    public:
        MeasurementCorruptionFunction(size_t seed, double likelihood):
            CorruptionFunction(seed, likelihood) {}
        MeasurementCorruptionFunction() = default;  // Default constructor needed for deserialization
};
SER20_REGISTER_TYPE(MeasurementCorruptionFunction);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(MeasurementCorruptionFunction);

/**
 * Abstract class for corruption functions that only apply to ControlReeceived events
 */
class ControlCorruptionFunction: public CorruptionFunction {
    public:
        ControlCorruptionFunction(size_t seed, double likelihood):
            CorruptionFunction(seed, likelihood) {}
        ControlCorruptionFunction() = default;  // Default constructor needed for deserialization
};
SER20_REGISTER_TYPE(ControlCorruptionFunction);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(ControlCorruptionFunction);

class NoCorruption: public CorruptionFunction {
    public:
        NoCorruption(size_t seed, double likelihood): CorruptionFunction(seed, likelihood) {}
        NoCorruption() = default;  // Default constructor needed for deserialization
        void apply(MeasurementReceived& info) final override { (void) info; };
        void apply(ControlReceived& info) final override { (void) info; };
};
SER20_REGISTER_TYPE(NoCorruption);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(NoCorruption);

class RandomNoiseMeasurementCorruption: public MeasurementCorruptionFunction {
    public:
        RandomNoiseMeasurementCorruption(size_t seed, double likelihood, std::pair<double, double> noise_range) :
            MeasurementCorruptionFunction(seed, likelihood),
            noise_range_(noise_range) {}
        RandomNoiseMeasurementCorruption() = default;  // Default constructor needed for deserialization

        /**
         * Add random noise to the measurement value
         */
        void apply(MeasurementReceived& info) override;
        void apply(ControlReceived& info) override { (void) info; };  // Do not act on controls

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<MeasurementCorruptionFunction>(this), noise_range_);
        }

    private:
        std::pair<double, double> noise_range_;
};
SER20_REGISTER_TYPE(RandomNoiseMeasurementCorruption);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(RandomNoiseMeasurementCorruption);

class RandomNoiseControlCorruption: public ControlCorruptionFunction {
    public:
        RandomNoiseControlCorruption(size_t seed, double likelihood, std::pair<double, double> noise_range) :
            ControlCorruptionFunction(seed, likelihood),
            noise_range_(noise_range) {}
        RandomNoiseControlCorruption() = default;  // Default constructor needed for deserialization

        /**
         * Add random noise to the control value
         */
        void apply(ControlReceived& info) override;
        void apply(MeasurementReceived& info) override { (void) info; };  // Do not act on measurements

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<ControlCorruptionFunction>(this), noise_range_);
        }

    private:
        std::pair<double, double> noise_range_;
};
SER20_REGISTER_TYPE(RandomNoiseControlCorruption);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(RandomNoiseControlCorruption);

class ZeroOutMeasurementCorruption: public MeasurementCorruptionFunction {
    public:
        ZeroOutMeasurementCorruption(size_t seed, double likelihood, double zero_value):
            MeasurementCorruptionFunction(seed, likelihood),
            zero_value_(zero_value) {}
        ZeroOutMeasurementCorruption() = default;  // Default constructor needed for deserialization

        /**
         * Zero out the measurement value
         */
        void apply(MeasurementReceived& info) override;
        void apply(ControlReceived& info) override { (void) info; };  // Do not act on controls

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<MeasurementCorruptionFunction>(this), zero_value_);
        }

    protected:
        double zero_value_;
};
SER20_REGISTER_TYPE(ZeroOutMeasurementCorruption);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(ZeroOutMeasurementCorruption);

class ShiftMeasurementCorruption: public MeasurementCorruptionFunction {
    public:
        ShiftMeasurementCorruption(size_t seed, double likelihood, double shift_value):
            MeasurementCorruptionFunction(seed, likelihood),
            shift_value_(shift_value) {}
        ShiftMeasurementCorruption() = default;  // Default constructor needed for deserialization

        /**
         * Shift the measurement value by a constant factor
         */
        void apply(MeasurementReceived& info) override;
        void apply(ControlReceived& info) override { (void) info; };  // Do not act on controls

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<MeasurementCorruptionFunction>(this), shift_value_);
        }

    protected:
        double shift_value_;
};
SER20_REGISTER_TYPE(ShiftMeasurementCorruption);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(ShiftMeasurementCorruption);

class InvertControlCorruption: public ControlCorruptionFunction {
    public:
        InvertControlCorruption(size_t seed, double likelihood, double invert_factor=-1):
            ControlCorruptionFunction(seed, likelihood),
            invert_factor_(invert_factor) {}
        InvertControlCorruption() = default;  // Default constructor needed for deserialization

        /**
         * Invert the control value
         */
        void apply(ControlReceived& info) override;
        void apply(MeasurementReceived& info) override { (void) info; };  // Do not act on measurements

        template<class Archive>
        void serialize(Archive& ar) {
            ar(ser20::base_class<ControlCorruptionFunction>(this), invert_factor_);
        }

    protected:
        double invert_factor_;
};
SER20_REGISTER_TYPE(InvertControlCorruption);  // Necessary for polymorphic types
CHECK_SERIALIZABLE(InvertControlCorruption);

enum class CorruptionFunctions {
    NoCorruption,
    ControlNoCorruption,
    RandomNoiseMeasurementCorruption,
    RandomNoiseControlCorruption,
    ZeroOutMeasurementCorruption,
    ShiftMeasurementCorruption,
    InvertControlCorruption
};

[[maybe_unused]] static CorruptionFunctions stringToCorruptionFunction(const std::string& str) {
    if (str == "NoCorruption") return CorruptionFunctions::NoCorruption;
    if (str == "RandomNoiseMeasurementCorruption")  return CorruptionFunctions::RandomNoiseMeasurementCorruption;
    if (str == "RandomNoiseControlCorruption")  return CorruptionFunctions::RandomNoiseControlCorruption;
    if (str == "ZeroOutMeasurementCorruption")  return CorruptionFunctions::ZeroOutMeasurementCorruption;
    if (str == "ShiftMeasurementCorruption") return CorruptionFunctions::ShiftMeasurementCorruption;
    if (str == "InvertControlCorruption")  return CorruptionFunctions::InvertControlCorruption;
    throw std::invalid_argument("Unknown corruption function type " + str);
}

#endif // CORRUPTION_FUNCTIONS_H
