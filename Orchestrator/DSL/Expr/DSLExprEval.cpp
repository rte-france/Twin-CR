/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLExprEval.h"

#include <stdexcept>

std::optional<double> ArithmeticExpression::evaluate(const DSLValueCache& cache) const {
    std::string type = expr.at("type");
    if (type == "const") {
        return expr.at("value").get<double>();
    }
    if (type == "var") {
        return cache.get(expr.at("id").get<std::string>());
    }
    if (type == "arith") {
        auto left = ArithmeticExpression{expr.at("left")}.evaluate(cache);
        auto right = ArithmeticExpression{expr.at("right")}.evaluate(cache);
        if (!left || !right) return std::nullopt;
        std::string op = expr.at("op");
        if (op == "+") return *left + *right;
        if (op == "-") return *left - *right;
        if (op == "*") return *left * *right;
        if (op == "/") return *left / *right;
        throw std::invalid_argument("Unknown arithmetic operator: " + op);
    }
    throw std::invalid_argument("Not an arithmetic expression node: " + type);
}

bool BooleanExpression::evaluate(const DSLValueCache& cache) const {
    std::string type = expr.at("type");
    if (type == "bool") {
        return expr.at("value").get<bool>();
    }
    if (type == "cmp") {
        auto left = ArithmeticExpression{expr.at("left")}.evaluate(cache);
        auto right = ArithmeticExpression{expr.at("right")}.evaluate(cache);
        if (!left || !right) {
            return false;  // missing live value -> always return false
        }
        std::string op = expr.at("op");
        if (op == "<") return *left < *right;
        if (op == ">") return *left > *right;
        if (op == "<=") return *left <= *right;
        if (op == ">=") return *left >= *right;
        if (op == "==") return *left == *right;
        if (op == "!=") return *left != *right;
        throw std::invalid_argument("Unknown comparison operator: " + op);
    }
    if (type == "and") {
        for (auto& operand : expr.at("operands")) {
            if (!BooleanExpression{operand}.evaluate(cache)) {
                return false;
            }
        }
        return true;
    }
    if (type == "or") {
        for (auto& operand : expr.at("operands")) {
            if (BooleanExpression{operand}.evaluate(cache)) {
                return true;
            }
        }
        return false;
    }
    throw std::invalid_argument("Not a boolean expression node: " + type);
}

static void collectReferencedIdsInto(const nlohmann::json& expr, std::unordered_set<std::string>& ids) {
    if (!expr.is_object()) return;  // e.g. an `after` trigger's unused condition expression
    std::string type = expr.value("type", std::string());
    if (type == "var") {
        ids.insert(expr.at("id").get<std::string>());
    } else if (type == "arith" || type == "cmp") {
        collectReferencedIdsInto(expr.at("left"), ids);
        collectReferencedIdsInto(expr.at("right"), ids);
    } else if (type == "and" || type == "or") {
        for (auto& operand : expr.at("operands")) {
            collectReferencedIdsInto(operand, ids);
        }
    }
    // "const"/"bool": no ids referenced
}

std::unordered_set<std::string> collectReferencedIds(const nlohmann::json& expr) {
    std::unordered_set<std::string> ids;
    collectReferencedIdsInto(expr, ids);
    return ids;
}
