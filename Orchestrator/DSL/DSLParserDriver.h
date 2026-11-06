/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef DSL_PARSER_DRIVER_H
#define DSL_PARSER_DRIVER_H

#include "PowerEventDSLLexer.h"
#include "PowerEventDSLParser.h"

#include <antlr4-runtime.h>

#include <memory>
#include <string>

/**
 * Aborts on the first lexer/parser syntax error by throwing std::invalid_argument, instead of ANTLR's default
 * behavior (print to stderr, attempt error recovery, and hand back a best-effort/possibly-malformed parse tree).
 * Visiting such a malformed tree later crashes on unchecked null sub-context accessors in DSLProgramVisitor.
 */
class ThrowingDSLErrorListener : public antlr4::BaseErrorListener {
    public:
        void syntaxError(antlr4::Recognizer* recognizer, antlr4::Token* offendingSymbol, size_t line,
                          size_t charPositionInLine, const std::string& msg, std::exception_ptr e) override;
};

/**
 * Parses a piece of PowerEventDSL source text into an ANTLR parse tree, and keeps the lexer/token-stream/parser alive for as long as the returned tree
 * is used (a function body is re-visited on every call with fresh argument bindings, so trees can't be parsed-and-discarded the way a typical
 * one-shot parse would).
 * Throws std::invalid_argument on the first syntax error (see ThrowingDSLErrorListener).
 */
class DSLParseResult {
    public:
        DSLParseResult(const std::string& source);

        PowerEventDSLParser::ProgramContext* program() { return program_; }

    private:
        std::string source_;
        antlr4::ANTLRInputStream input_;
        PowerEventDSLLexer lexer_;
        antlr4::CommonTokenStream tokens_;
        PowerEventDSLParser parser_;
        PowerEventDSLParser::ProgramContext* program_;
        ThrowingDSLErrorListener error_listener_;
};

/**
 * Parses a function body (re-visited at every call site, with fresh argument bindings)
 * Since FunctionDefinition keeps only the raw body text), we wraps it in a throwaway "func __fragment__() { <body> }"
 */
std::unique_ptr<DSLParseResult> parseFunctionBody(const std::string& body_text);

#endif // DSL_PARSER_DRIVER_H
