/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_FUNCTION_DEFINITION_H
#define DSL_FUNCTION_DEFINITION_H

#include "SerialisationHelper.h"

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

/**
 * A function is kept as plain data (name, param names, raw body source text) and re-parsed at every call site for easy (de)serialisation
 * Note that this cause function calls to be dynamically scoped (i.e. a function evaluate the scope at its call site and not at its declaration site),
 * i.e. calling a function is equivalent to copy pasting it content (with arguments resolved and propagating the tag of the function call if any)
 */
struct FunctionDefinition {
    std::string name;
    std::vector<std::string> param_names;
    std::string body_text; // the raw '{' ... '}' source, without the braces

    template<class Archive>
    void serialize(Archive& ar) { ar(name, param_names, body_text); }
};
CHECK_SERIALIZABLE(FunctionDefinition);

using FunctionTable = std::unordered_map<std::string, std::shared_ptr<FunctionDefinition>>;

#endif // DSL_FUNCTION_DEFINITION_H
