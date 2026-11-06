/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef SERIALISATION_HELPER_H
#define SERIALISATION_HELPER_H

#include "Tase2.h"

#include <graaflib/graph.h>
#include <nlohmann/json.hpp>
#include <ser20/ser20.hpp>
#include <ser20/archives/binary.hpp>
#include <ser20/details/traits.hpp>
#include <ser20/types/optional.hpp>
#include <ser20/types/string.hpp>
#include <ser20/types/vector.hpp>
#include <ser20/types/memory.hpp>
#include <ser20/types/unordered_map.hpp>
#include <ser20/types/unordered_set.hpp>
#include <ser20/types/polymorphic.hpp>
#include <ser20/types/utility.hpp>  // for std::pair
#include <random>
#include <sstream>

#define CHECK_SERIALIZABLE(Type) static_assert(::ser20::traits::detail::count_output_serializers<Type, ::ser20::BinaryOutputArchive> == 1, #Type " is missing output serialization for BinaryOutputArchive")

namespace nlohmann {
    template<class Archive>
    void serialize(Archive& ar, json& j) {
        std::string s;
        if (Archive::is_saving::value) s = j.dump();
        ar(s);
        if (Archive::is_loading::value) j = json::parse(s);
    }
}

namespace ser20 {

// Serialisation of mt19937
template <class Archive>
void save(Archive& ar, const std::mt19937& rng) {
    std::ostringstream oss;
    oss << rng;
    std::string state = oss.str();
    ar(state);
}

template <class Archive>
void load(Archive& ar, std::mt19937& rng) {
    std::string state;
    ar(state);
    std::istringstream iss(state);
    iss >> rng;
}

// Serialisation of uniform_real_distribution
template<class Archive, typename  T>
void save(Archive& ar, const std::uniform_real_distribution<T>& dist) {
    ar(dist.a(), dist.b());
}

template<class Archive, typename T>
void load(Archive& ar, std::uniform_real_distribution<T>& dist) {
    T a, b;
    ar(a, b);
    dist = std::uniform_real_distribution<T>(a, b);
}

// Serialisation of normal_distribution
template<class Archive, typename T>
void save(Archive& ar, const std::normal_distribution<T>& dist) {
    ar(dist.mean(), dist.stddev());
}

template<class Archive, typename T>
void load(Archive& ar, std::normal_distribution<T>& dist) {
    T mean, stddev;
    ar(mean, stddev);
    dist = std::normal_distribution<T>(mean, stddev);
}

template <class Archive>
void save(Archive& ar, const tase2::Tase2Extension& ext) {
    ar(ext.tase2_id, ext.signalisation_type, ext.cause, ext.validity, ext.operator_blocked);
}

template <class Archive>
void load(Archive& ar, tase2::Tase2Extension& ext) {
    ar(ext.tase2_id, ext.signalisation_type, ext.cause, ext.validity, ext.operator_blocked);
}

}

#endif // SERIALISATION_HELPER_H
