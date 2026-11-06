/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef VALUE_H
#define VALUE_H

#include <variant>

#include <fmt/core.h>
#include <nlohmann/json.hpp>

using value_type = std::variant<bool, int, double>;

/**
 * Value that can be given either as bool, int or double
 */
struct Value {
    Value(value_type v): value(v) {};
    Value(): value(0.0) {};
    Value(bool v): value(v) {};
    Value(int v): value(v) {};
    Value(double v): value(v) {};
    Value(const nlohmann::json::basic_json::value_type& j) {
        if (j.is_boolean()) {
            value = j.get<bool>();
        } else if (j.is_number_integer()) {
            value = j.get<int>();
        } else if (j.is_number_float()) {
            value = j.get<double>();
        } else {
            throw std::invalid_argument("'value' is not a supported type (bool, int or double)");
        }
    }

    value_type value;

    /**
     * Update the value based on a double
     */
    void update(double d) {
        std::visit([&](auto&& arg) {
            using T = std::decay_t<decltype(arg)>;
            if constexpr (std::is_same_v<T, bool>)
                arg = d >= 0.5;
            else if constexpr (std::is_same_v<T, int>)
                arg = static_cast<int>(std::round(d));
            else
                arg = d;
        }, value);
    }

    bool to_bool() const {
        return std::visit([&](auto&& arg) {
            using T = std::decay_t<decltype(arg)>;
            if constexpr (std::is_same_v<T, bool>)
                return arg;
            else
                return arg >= 0.5;
        }, value);
    }

    double to_double() const {
        return std::visit([&](auto&& arg) {
            return double(arg);
        }, value);
    }

    friend std::ostream& operator<<(std::ostream& os, const Value& v) {
        std::visit([&](auto&& arg) {
            os << arg;
        }, v.value);
        return os;
    }

    template<class Archive>
    void serialize(Archive& ar) {
        ar(value);
    }

    std::string to_string() const {
        return std::visit([&](auto&& arg) {
            return std::to_string(arg);
        }, value);
    }

    nlohmann::json to_json() const {
        return std::visit([](const auto& v) -> nlohmann::json {
            return v;
        }, value);
    }

    bool operator!=(const Value& other) const {
        return value != other.value;  // Note: (int) 1 != (double) 1.0 with this default implementation (could use to_double instead)
    }
};

template <>
struct fmt::formatter<Value> {
    constexpr auto parse(fmt::format_parse_context& ctx) {
        return ctx.begin();
    }

    template <typename FormatContext>
    auto format(const Value& v, FormatContext& ctx) const {
        return std::visit([&](auto&& arg) {
            return fmt::format_to(ctx.out(), "{}", arg);
        }, v.value);
    }
};

#endif // VALUE_H
