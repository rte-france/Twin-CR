/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef TASE2_H
#define TASE2_H

#include "Value.h"

#include <fmt/core.h>

namespace tase2 {

// Quality definition from libiec61850
constexpr int QUALITY_VALIDITY_GOOD = 0;
constexpr int QUALITY_VALIDITY_INVALID = 2;
constexpr int QUALITY_VALIDITY_RESERVED = 1;
constexpr int QUALITY_VALIDITY_QUESTIONABLE = 3;

// Causes from https://lf-energy.atlassian.net/wiki/spaces/FLED/pages/13675948/Cause+of+Transmission
constexpr int CAUSE_PERIODIC = 1;
constexpr int CAUSE_SPONTANEOUS = 3;
constexpr int CAUSE_ACTIVATION_CONFIRMATION = 7;  // Acknowledgement of a control

enum class SignalisationType : int32_t {
    TS = 0,  // Télésignalisation : Transmission of state information (open/closed, on/off)
    TC = 1,  // Télécommande : Transmission of control commands
    TVC = 2,  // Télécommande avec Validation et Contrôle : Secure commands requiring validation
    TM = 3,  // Télémesure : Transmission of numerical values (voltage, current, powers, etc.)
    GI = 4  // General interrogation: synchronisation command sent to RTUs
};

inline std::string to_string(SignalisationType t) {
    switch (t) {
        case SignalisationType::TS:  return "TS";
        case SignalisationType::TC:  return "TC";
        case SignalisationType::TVC: return "TVC";
        case SignalisationType::TM:  return "TM";
        case SignalisationType::GI:  return "GI";
        default: throw std::invalid_argument("Unknown SignalisationType: " + std::to_string(static_cast<int32_t>(t)));
    }
}

inline std::ostream& operator<<(std::ostream& os, SignalisationType t) {
    return os << to_string(t);
}

inline SignalisationType parseSignalisationType(const nlohmann::json& j) {
    if (j.is_string()) {
        const std::string& s = j.get<std::string>();
        if (s == "TS")  return SignalisationType::TS;
        if (s == "TC")  return SignalisationType::TC;
        if (s == "TVC") return SignalisationType::TVC;
        if (s == "TM")  return SignalisationType::TM;
        if (s == "GI")  return SignalisationType::GI;
        throw std::invalid_argument("Unknown SignalisationType string: " + s);
    }
    throw std::invalid_argument("SignalisationType must be a string, got: " + j.dump());
}

struct IEC61850Timestamp {
    uint32_t seconds_since_epoch;
    uint32_t fraction_of_second;  // 24-bit fractional part (8 first bits should be skipped)

    /**
     * fraction is converted from a double in [0,1) seconds to 24-bit binary fraction (https://lf-energy.atlassian.net/wiki/spaces/FLED/pages/13676099/CDC+measured+value+MVTyp)
     */
    IEC61850Timestamp(uint32_t seconds, double fraction) {
        seconds_since_epoch = seconds;
        fraction_of_second = static_cast<uint32_t>(fraction * (1 << 24));
    }
};

inline IEC61850Timestamp time_to_IEC61850(double time, double init_seconds_since_epoch) {
    double total = init_seconds_since_epoch + time;
    double whole_seconds;
    double fractional_seconds = std::modf(total, &whole_seconds);
    return IEC61850Timestamp(static_cast<uint32_t>(whole_seconds), fractional_seconds);
}

struct Tase2Extension {
    std::string tase2_id;
    SignalisationType signalisation_type;
    int cause;
    int validity;
    bool operator_blocked;
};

inline void appendTSField(fmt::memory_buffer& buf, const std::string& tase2_id, const Value& value, double time_sent, double init_seconds_since_epoch, int cause, int validity, bool operator_blocked) {
    IEC61850Timestamp ts = time_to_IEC61850(time_sent, init_seconds_since_epoch);
    fmt::format_to(std::back_inserter(buf),
        R"(,"tase2":{{"tase2_id":"{}","cause":{},"validity":{},"operatorBlocked":{},"stVal":{},"ts":{},"tfos":"{:024b}"}})",
        tase2_id, cause, validity, operator_blocked, value, ts.seconds_since_epoch, ts.fraction_of_second);

    // TODO: stVal should be one bit for single point, two bits for double points
    // Below not included
    // "isGenuine": Boolean, // Optional (default value: true)
    // "tsValidity": Boolean, // Optional, timestamp validity (default: true)
}

inline void appendTMField(fmt::memory_buffer& buf, const std::string& tase2_id, const Value& value, double time_sent, double init_seconds_since_epoch, int cause, int validity, bool operator_blocked) {
    IEC61850Timestamp ts = time_to_IEC61850(time_sent, init_seconds_since_epoch);
    fmt::format_to(std::back_inserter(buf),
        R"(,"tase2":{{"tase2_id":"{}","cause":{},"validity":{},"operatorBlocked":{},"value":{},"ts":{},"tfos":"{:024b}"}})",
        tase2_id, cause, validity, operator_blocked, value, ts.seconds_since_epoch, ts.fraction_of_second);

    // Below not included
    // "isGenuine": Boolean, // Optional (default value: true)
    // "tsValidity": Boolean, // Optional, timestamp validity (default: true)
}

inline void appendTase2Field(fmt::memory_buffer& buf, const std::string& tase2_id, const Value& value, double time_sent, double init_seconds_since_epoch, int cause, int validity, bool operator_blocked, SignalisationType signalisation_type) {
    switch (signalisation_type) {
        case SignalisationType::TS:
            appendTSField(buf, tase2_id, value, time_sent, init_seconds_since_epoch, cause, validity, operator_blocked);
            break;
        case SignalisationType::TM:
            appendTMField(buf, tase2_id, value, time_sent, init_seconds_since_epoch, cause, validity, operator_blocked);
            break;
        case SignalisationType::TC:
        case SignalisationType::TVC:
        case SignalisationType::GI:
            // TODO: handle TC, TVC, GI signalisation types
            break;
    }
}

inline int getDefaultCause(const SignalisationType& type) {
    switch (type) {
        case SignalisationType::TM:
            return CAUSE_PERIODIC;
        case SignalisationType::TS:
        case SignalisationType::TC:
        case SignalisationType::TVC:
        case SignalisationType::GI:
            return CAUSE_SPONTANEOUS;
        default:
            throw;
    }
}

inline std::optional<Tase2Extension> parseTase2Extension(const nlohmann::json& message) {
    if (!message.contains("tase2") || message["tase2"].is_null()) {
        return std::nullopt;
    }
    const auto& t = message["tase2"];
    auto type = parseSignalisationType(t["signalisation_type"]);
    return Tase2Extension(
        t["tase2_id"].get<std::string>(),
        type,
        t.value("cause", getDefaultCause(type)),
        t.value("validity", QUALITY_VALIDITY_GOOD),
        t.value("operatorBlocked", false)
    );
}

}  // Namespace tase2

template <>
struct fmt::formatter<tase2::SignalisationType> : fmt::formatter<std::string_view> {
    auto format(tase2::SignalisationType t, fmt::format_context& ctx) const {
        return fmt::formatter<std::string_view>::format(to_string(t), ctx);
    }
};

#endif // TASE2_H
