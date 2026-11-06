#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for ScenarioHandler library

# Add the library
add_library(scenariohandler)

# Set the language explicitly to C++
set_target_properties(scenariohandler PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB SCENARIO_HANDLER_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "SCENARIO_HANDLER_SOURCES: ${SCENARIO_HANDLER_SOURCES}")

target_sources(scenariohandler PRIVATE ${SCENARIO_HANDLER_SOURCES})

# Include directories
target_include_directories(scenariohandler
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link the scenariohandler library
target_link_libraries(scenariohandler PUBLIC
    broker
    dynawointerface
    informationflowmodel
    )
