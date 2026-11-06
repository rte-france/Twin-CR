#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# DSL regression cases. Each case directory under cases/ becomes one CTest entry, so `make test` reports them
# individually. They are fast (no Dynawo, no NATS, no ClickHouse) and are meant to be run on every build.
add_executable(dsl_test DslTestRunner.cpp)

target_link_libraries(dsl_test PRIVATE
    dsl
    testing
    tomlplusplus::tomlplusplus
    spdlog
)

# Load resource files
set(DSL_TEST_RESOURCES "${CMAKE_CURRENT_SOURCE_DIR}/resources")
target_compile_definitions(dsl_test PRIVATE
    NORDIC_NETWORK_FILE="${DSL_TEST_RESOURCES}/Nordic.xiidm"
    NORDIC_OUTPUTS_FILE="${DSL_TEST_RESOURCES}/game_master_outputs.json"
    NORDIC_INPUTS_FILE="${DSL_TEST_RESOURCES}/game_master_inputs.json"
)

file(GLOB DSL_TEST_CASES ${CMAKE_CURRENT_SOURCE_DIR}/cases/*)
foreach(case_dir ${DSL_TEST_CASES})
    if(IS_DIRECTORY ${case_dir})
        get_filename_component(case_name ${case_dir} NAME)
        add_test(NAME dsl.${case_name} COMMAND dsl_test ${case_dir})
        set_tests_properties(dsl.${case_name} PROPERTIES LABELS dsl TIMEOUT 60)
    endif()
endforeach()

# The reserved-word lists used by the LaTeX reference and by the Argus editor are generated from the grammar.
find_package(Python3 COMPONENTS Interpreter QUIET)
if(Python3_Interpreter_FOUND)
    add_test(NAME dsl.keywords_up_to_date
             COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/extract_keywords.py --check)
    set_tests_properties(dsl.keywords_up_to_date PROPERTIES LABELS dsl TIMEOUT 60)
else()
    message(STATUS "Python3 not found: skipping the dsl.keywords_up_to_date test")
endif()

# `ctest` at the top level also runs whatever the fetched dependencies register, which is hundreds of unrelated
# tests, so give this suite its own entry point: `make dsl-tests` runs these cases and nothing else.
add_custom_target(dsl-tests
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure --label-regex dsl
    DEPENDS dsl_test
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Running the DSL regression cases"
)
