/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef MODE_H
#define MODE_H

#include <stdexcept>
#include <string>

enum class Mode { Validate, Execute };

inline std::string to_string(Mode t) {
    switch (t) {
        case Mode::Validate: return "Validate";
        case Mode::Execute:  return "Execute";
        default: throw std::invalid_argument("Unknown Mode: " + std::to_string(static_cast<int32_t>(t)));
    }
}

#endif // MODE_H
