/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_EXPR_EVAL_H
#define DSL_EXPR_EVAL_H

#include "DSLValueCache.h"

#include <nlohmann/json.hpp>

#include <optional>
#include <string>
#include <unordered_set>

/**
 * `dynamicExpression` (used by `when`/`when_rearming`) can't be stored as a
 * std::function -- it must be re-evaluated every tick against live values,
 * and DSLConditionalEvent needs to serialize/reload cleanly. So it's resolved
 * by the visitor into a small JSON expression tree instead:
 *   {"type":"const","value":<double>}
 *   {"type":"var","id":"<string>"}                            -- live DSLValueCache lookup
 *   {"type":"arith","op":"+|-|*|/","left":{...},"right":{...}}
 *   {"type":"cmp","op":"<|>|<=|>=|==|!=","left":{...},"right":{...}}
 *   {"type":"and","operands":[...]}  |  {"type":"or","operands":[...]}
 *   {"type":"bool","value":true|false}
 * A missing live value (e.g. before the first ActualMeasurement/ActualControl
 * arrives for that id) makes any comparison depending on it evaluate to false.
 */
struct ArithmeticExpression {
    nlohmann::json expr; // a "const"/"var"/"arith" node, per the shape above

    std::optional<double> evaluate(const DSLValueCache& cache) const;
};

struct BooleanExpression {
    nlohmann::json expr; // a "bool"/"cmp"/"and"/"or" node, per the shape above

    bool evaluate(const DSLValueCache& cache) const;
};

/**
 * Collects every {"type":"var","id":...} leaf's id referenced anywhere in a boolean/arithmetic expression tree.
 * Used to know which ids a `when`/`when_rearming` condition actually needs, to add the necessary subscriptions in the DSLValueCache.
 */
std::unordered_set<std::string> collectReferencedIds(const nlohmann::json& expr);

#endif // DSL_EXPR_EVAL_H
