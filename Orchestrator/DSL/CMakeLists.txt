#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Generate C++ lexer/parser/listener/visitor from the grammar
set(DSL_GRAMMAR_FILE "${CMAKE_CURRENT_SOURCE_DIR}/PowerEventDSL.g4" CACHE FILEPATH
    "Path to the PowerEventDSL grammar file")
set(ANTLR_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")

# All files ANTLR produces with -visitor
set(ANTLR_GENERATED_SOURCES
    "${ANTLR_OUT_DIR}/PowerEventDSLLexer.cpp"
    "${ANTLR_OUT_DIR}/PowerEventDSLParser.cpp"
    "${ANTLR_OUT_DIR}/PowerEventDSLBaseListener.cpp"
    "${ANTLR_OUT_DIR}/PowerEventDSLListener.cpp"
    "${ANTLR_OUT_DIR}/PowerEventDSLBaseVisitor.cpp"
    "${ANTLR_OUT_DIR}/PowerEventDSLVisitor.cpp"
)

# envs/Dockerfile.orchestrator generates these ahead of time in a dedicated 'antlr-codegen' stage/layer,
# so use them if present. Else (local/non-Docker builds) fall back to generating on demand below.
set(ANTLR_PREGENERATED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../dsl-generated-prebuilt" CACHE PATH
    "If it already contains the ANTLR-generated sources, they are used as-is instead of re-running the ANTLR tool")

if(EXISTS "${ANTLR_PREGENERATED_DIR}/PowerEventDSLLexer.cpp")
    message(STATUS "Using pre-generated ANTLR sources from ${ANTLR_PREGENERATED_DIR}")
    file(MAKE_DIRECTORY "${ANTLR_OUT_DIR}")
    file(COPY "${ANTLR_PREGENERATED_DIR}/" DESTINATION "${ANTLR_OUT_DIR}")
    add_custom_target(dsl_antlr_generate)
else()
    # ANTLR4 tool jar (code generation only)
    set(ANTLR4_TAG "4.13.2")  # Version to keep in sync with envs/Dockerfile.orchestrator
    set(ANTLR4_JAR_URL "https://www.antlr.org/download/antlr-${ANTLR4_TAG}-complete.jar")
    set(ANTLR4_JAR "${CMAKE_BINARY_DIR}/antlr4-complete.jar")

    if(NOT EXISTS "${ANTLR4_JAR}")
        message(STATUS "Downloading ANTLR4 tool jar...")
        file(DOWNLOAD "${ANTLR4_JAR_URL}" "${ANTLR4_JAR}" SHOW_PROGRESS STATUS _dl_status)
        list(GET _dl_status 0 _dl_code)
        if(NOT _dl_code EQUAL 0)
            message(FATAL_ERROR "Failed to download ANTLR4 jar: ${_dl_status}")
        endif()
    endif()

    find_program(Java_JAVA_EXECUTABLE java REQUIRED)
    file(MAKE_DIRECTORY "${ANTLR_OUT_DIR}")

    add_custom_command(
        OUTPUT  ${ANTLR_GENERATED_SOURCES}
        COMMAND ${Java_JAVA_EXECUTABLE}
                -jar "${ANTLR4_JAR}"
                -Dlanguage=Cpp
                -visitor
                -o "${ANTLR_OUT_DIR}"
                "${DSL_GRAMMAR_FILE}"
        DEPENDS "${DSL_GRAMMAR_FILE}"
        COMMENT "Generating C++ parser from PowerEventDSL.g4"
        VERBATIM
    )
    add_custom_target(dsl_antlr_generate DEPENDS ${ANTLR_GENERATED_SOURCES})
endif()

# DSL library
add_library(dsl)
set_target_properties(dsl PROPERTIES LINKER_LANGUAGE CXX)

file(GLOB_RECURSE DSL_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp)
list(FILTER DSL_SOURCES EXCLUDE REGEX "/tests/")  # Exlude tests/ (which has its own main()) from the library
message(STATUS "DSL_SOURCES: ${DSL_SOURCES}")

# Only need CodeCompletionCore.cpp from ANTLR_C3
set(ANTLR4_C3_DIR "${antlr4_c3_SOURCE_DIR}/ports/cpp/source")
target_sources(dsl PRIVATE ${DSL_SOURCES} ${ANTLR_GENERATED_SOURCES}
    "${ANTLR4_C3_DIR}/antlr4-c3/CodeCompletionCore.cpp")
add_dependencies(dsl dsl_antlr_generate)

target_include_directories(dsl PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${ANTLR_OUT_DIR}
)

# BEFORE, and not SYSTEM: antlr4-c3 includes <Parser.h>, and a case-insensitive filesystem otherwise resolves it to nats' parser.h
target_include_directories(dsl BEFORE PRIVATE
    "${antlr4_runtime_SOURCE_DIR}/runtime/Cpp/runtime/src"
    "${ANTLR4_C3_DIR}"
)
# The antlr runtime headers (not SYSTEM, see above) hide overloaded virtual functions
target_compile_options(dsl PRIVATE -Wno-overloaded-virtual)

if(ORCHESTRATOR_BUILD_TESTS)
    add_subdirectory(tests)
endif()

target_link_libraries(dsl PUBLIC
    antlr4_static
    scenariohandler
    dynawointerface
    logger
    orchestrator
)
