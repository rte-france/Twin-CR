#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

add_library(alarms)

set_target_properties(alarms PROPERTIES LINKER_LANGUAGE CXX)

file(GLOB ALARMS_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

target_sources(alarms PRIVATE ${ALARMS_SOURCES})

target_include_directories(alarms
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(alarms
    PUBLIC
    orchestrator
    PRIVATE
    broker
    spdlog
    tomlplusplus::tomlplusplus
)

if(ORCHESTRATOR_BUILD_TESTS)
    add_subdirectory(tests)
endif()
