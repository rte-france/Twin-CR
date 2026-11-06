/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef TOML_EXTENSION_H
#define TOML_EXTENSION_H

#include <toml++/toml.h>

#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>


template <typename T>
T get_or_throw(const toml::table& tbl, const std::vector<std::string>& keys) {
    const toml::node* node = &tbl;

    for (const auto& key : keys) {
        if (auto table = node->as_table()) {
            node = table->get(key);
            if (!node) {
                std::ostringstream oss;
                oss << "Missing config path:";
                for (const auto& k : keys) {
                    oss << "['" << k << "']";
                }
                throw std::invalid_argument(oss.str() + " in config.toml");
            }
        } else {
            std::ostringstream oss;
            oss << "Expected table at path prefix:";
            for (const auto& k : keys) {
                oss << "['" << k << "']";
            }
            throw std::invalid_argument(oss.str() + " in config.toml");
        }
    }

    if (auto val = node->value<T>()) {
        return *val;
    }

    std::ostringstream oss;
    oss << "Key at path:";
    for (const auto& k : keys) {
        oss << "['" << k << "']";
    }
    oss << " exists but has incompatible type in config.toml";
    throw std::invalid_argument(oss.str());
}

template <typename T>
std::optional<T> get_or_continue(const toml::table &tbl, const std::vector<std::string> &keys) {
    try {
        return get_or_throw<T>(tbl, keys);
    } catch (std::invalid_argument &e) {
        return std::nullopt;
    }
}

#endif // TOML_EXTENSION_H
