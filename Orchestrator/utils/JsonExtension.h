/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef JSON_EXTENSION_H
#define JSON_EXTENSION_H

#include <nlohmann/json.hpp>

#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

inline nlohmann::json::json_pointer to_json_pointer(const std::vector<std::string>& keys) {
    nlohmann::json::json_pointer ptr;
    for (const auto& key : keys) {
        ptr.push_back(key);  // push_back takes raw (unescaped) tokens, so '~'/'/' in a key need no manual RFC 6901 escaping
    }
    return ptr;
}

template <typename T>
T get_or_throw(const nlohmann::json& j, const std::vector<std::string>& keys) {
    try {
        return j.at(to_json_pointer(keys)).get<T>();
    } catch (const nlohmann::json::out_of_range&) {
        std::ostringstream oss;
        oss << "Missing config path: ";
        for (const auto& k : keys) {
            oss << "['" << k << "']";
        }
        throw std::invalid_argument(oss.str() + " in\n" + j.dump());
    }
}

template <typename T>
std::optional<T> get_optional(const nlohmann::json& j, const std::vector<std::string>& keys) {
    auto ptr = to_json_pointer(keys);
    if (!j.contains(ptr) || j.at(ptr).is_null()) {
        return std::nullopt;
    }
    return j.at(ptr).get<T>();
}

template <typename T>
T get_or_default(const nlohmann::json& j, const std::vector<std::string>& keys, T default_) {
    return get_optional<T>(j, keys).value_or(default_);
}

#endif // JSON_EXTENSION_H
