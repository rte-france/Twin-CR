/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef SERIALIZATION_H
#define SERIALIZATION_H

#include "Tase2.h"

#include <cstdint>
#include <string>
#include <iostream>
#include <variant>

#include <fmt/core.h>
#include <nlohmann/json.hpp>
#include <ser20/types/variant.hpp>

class ClickHouseBinaryBuffer {
public:
    std::string buffer;

    template <typename T>
    void write(const T& val) {
        static_assert(std::is_trivially_copyable<T>::value, "Must be POD");
        buffer.append(reinterpret_cast<const char*>(&val), sizeof(T));
    }

    // Clickhouse expects variable-length unsigned integer (a.k.a. VarUInt) instead of a simple size_t/uint64
    // cf https://github.com/ClickHouse/ClickHouse/blob/master/src/IO/VarInt.h
    void writeVarUInt(uint64_t x) {
        while (x >= 0x80) {
            buffer.push_back(static_cast<char>(x | 0x80));
            x >>= 7;
        }
        buffer.push_back(static_cast<char>(x));
    }

    void writeString(const std::string& str) {
        writeVarUInt(str.size());
        buffer.append(str);
    }

    void writeValue(const Value& value) {
        std::visit([&](auto&& arg) {
            using T = std::decay_t<decltype(arg)>;
            uint8_t tag;
            if constexpr (std::is_same_v<T, bool>) tag = 0;
            else if constexpr (std::is_same_v<T, int>) tag = 1;
            else if constexpr (std::is_same_v<T, double>) tag = 2;
            write(tag);
        }, value.value);
        // Always write value as double (must match clickhouse table format), and use tag to store the actual type
        write(value.to_double());
    }

    const char* data() const { return buffer.data(); }
    size_t size() const { return buffer.size(); }
    void clear() { buffer.clear(); }
};

inline void serialize(ClickHouseBinaryBuffer&) {}

template <typename T>
struct is_optional : std::false_type {};
template <typename T>
struct is_optional<std::optional<T>> : std::true_type {};

// Recursive variadic template
template <typename T, typename... Rest>
void serialize(ClickHouseBinaryBuffer& buf, const T& first, const Rest&... rest) {
    if constexpr (std::is_same_v<std::decay_t<T>, std::string>) {
        buf.writeString(first);
    } else if constexpr (std::is_same_v<std::decay_t<T>, const char*> ||  // Serialize c-style strings like normal ones
                         std::is_same_v<std::decay_t<T>, char*>) {
        buf.writeString(std::string(first));
    } else if constexpr (std::is_same_v<std::decay_t<T>, Value>) {
        buf.writeValue(first);
    } else if constexpr (is_optional<std::decay_t<T>>::value) {
        // For all Nullable columns, write 0x00 + value if non null, else 0x01
        if constexpr (std::is_same_v<typename std::decay_t<T>::value_type, tase2::Tase2Extension>) {
            if (first.has_value()) {
                buf.write(uint8_t(0)); buf.writeString(first->tase2_id);
                buf.write(uint8_t(0)); buf.write(first->signalisation_type);
                buf.write(uint8_t(0)); buf.write(first->cause);
                buf.write(uint8_t(0)); buf.write(first->validity);
                buf.write(uint8_t(0)); buf.write(first->operator_blocked);
            } else {
                buf.write(uint8_t(1));
                buf.write(uint8_t(1));
                buf.write(uint8_t(1));
                buf.write(uint8_t(1));
                buf.write(uint8_t(1));
            }
        } else {
            buf.write(first.has_value() ? uint8_t(0) : uint8_t(1));
            if (first.has_value()) {
                serialize(buf, *first);
            }
        }
    } else {
        static_assert(std::is_trivially_copyable_v<std::decay_t<T>>, "Unsupported type in serialize — add a specialization for this type");
        buf.write(first);
    }
    if constexpr (sizeof...(rest) > 0) {
        serialize(buf, rest...);
    }
}

class VectorStreamBuf : public std::streambuf {
public:
    VectorStreamBuf(const char* base, size_t size) {
        char* p = const_cast<char*>(base);
        setg(p, p, p + size);
    }
};

class ClickHouseBinaryReader {
    std::vector<char> buffer_;
    VectorStreamBuf vsbuf_;
    std::istream in;

public:
    explicit ClickHouseBinaryReader(std::vector<char>&& buffer) : buffer_(std::move(buffer)), vsbuf_(buffer_.data(), buffer_.size()), in(&vsbuf_) {}

    int peek() {
        return in.peek();
    }

    // Generic binary read
    template <typename T>
    void deserialize(T& val) {
        static_assert(std::is_trivially_copyable<T>::value, "Must be POD");
        if (!in.read(reinterpret_cast<char*>(&val), sizeof(T)))
            throw std::runtime_error("Unexpected EOF while reading POD type");
    }

    // Clickhouse expects variable-length unsigned integer (a.k.a. VarUInt) instead of a simple size_t/unint64
    // cf https://github.com/ClickHouse/ClickHouse/blob/master/src/IO/VarInt.h
    void deserialize(uint64_t& out) {
        out = 0;
        for (int shift = 0; shift < 64; shift += 7) {
            char byte;
            if (!in.get(byte))
                throw std::runtime_error("Unexpected EOF while reading VarUInt");
            out |= static_cast<uint64_t>(byte & 0x7F) << shift;
            if (!(byte & 0x80)) return;
        }
        throw std::runtime_error("VarUInt too long");
    }

    // Read a string prefixed by its length as VarUInt
    void deserialize(std::string& str) {
        uint64_t len = 0;
        deserialize(len);
        str.resize(len);
        // in.read(&str[0], len);
        if (!in.read(&str[0], len))
            throw std::runtime_error("Unexpected EOF while reading string");
    }

    void deserialize(Value& value) {
        uint8_t tag;
        double value_d;
        deserialize(tag);
        deserialize(value_d);
        // Cast back double value to the original type
        switch (tag) {
            case 0: {
                value.value = bool(value_d);
                break;
            }
            case 1: {
                value.value = int(value_d);
                break;
            }
            case 2: {
                value.value = double(value_d);
                break;
            }
            default:
                throw std::runtime_error("Unknown type tag in Value deserialization");
        }
    }

    void deserialize(std::optional<tase2::Tase2Extension>& ext) {
        std::optional<std::string> tase2_id;
        std::optional<tase2::SignalisationType> signalisation_type;
        std::optional<int> cause;
        std::optional<int> validity;
        std::optional<bool> operator_blocked;
        deserialize(tase2_id);
        deserialize(signalisation_type);
        deserialize(cause);
        deserialize(validity);
        deserialize(operator_blocked);

        if (tase2_id.has_value() && signalisation_type.has_value() && cause.has_value() && validity.has_value() && operator_blocked.has_value()) {
            ext.emplace(*tase2_id, *signalisation_type, *cause, *validity, *operator_blocked);
        }
    }

    template <typename T>
    void deserialize(std::optional<T>& opt) {
        uint8_t is_null;
        deserialize(is_null);
        if (!is_null) {
            opt = T{};
            deserialize(*opt);
        } else {
            opt = std::nullopt;
        }
    }

    // Variadic reader
    template <typename First, typename... Rest>
    void deserialize(First& first, Rest&... rest) {
        deserialize(first);
        if constexpr (sizeof...(rest) > 0)
            deserialize(rest...);
    }
};

#endif // SERIALIZATION_H
