/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef ENVIRONMENT_VARIABLE_H
#define ENVIRONMENT_VARIABLE_H

#include <cctype>
#include <cstdlib>
#include <string>

inline std::string getEnvironmentVariableOrDefault(const std::string& env, const std::string& default_value) {
    const char* env_value = std::getenv(env.c_str());
    if (env_value != nullptr) {
        return env_value;
    }
    return default_value;
}

/**
 * Reads a boolean flag from the environment, treating "1"/"true"/"yes" as true and
 * everything else, including an unset variable, as false.
 */
inline bool isEnvironmentVariableTrue(const std::string& env) {
    std::string value = getEnvironmentVariableOrDefault(env, "false");
    for (auto& c : value) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    return value == "1" || value == "true" || value == "yes";
}

#endif // ENVIRONMENT_VARIABLE_H
