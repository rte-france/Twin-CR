/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "DSLParserDriver.h"

#include <stdexcept>

void ThrowingDSLErrorListener::syntaxError(antlr4::Recognizer* /*recognizer*/, antlr4::Token* /*offendingSymbol*/,
                                            size_t line, size_t charPositionInLine, const std::string& msg,
                                            std::exception_ptr /*e*/) {
    throw std::invalid_argument("DSL syntax error at " + std::to_string(line) + ":"
        + std::to_string(charPositionInLine) + ": " + msg);
}

DSLParseResult::DSLParseResult(const std::string& source) :
source_(source),
input_(source_),
lexer_(&input_),
tokens_(&lexer_),
parser_(&tokens_) {
    lexer_.removeErrorListeners();
    lexer_.addErrorListener(&error_listener_);  // Throw on first error
    parser_.removeErrorListeners();
    parser_.addErrorListener(&error_listener_);
    program_ = parser_.program();
}

std::unique_ptr<DSLParseResult> parseFunctionBody(const std::string& body_text) {
    std::string wrapped = "func __fragment__() {\n" + body_text + "\n}\n";
    return std::make_unique<DSLParseResult>(wrapped);
}
