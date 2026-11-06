#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for GameMasterInterface library

# Add the library
add_library(gamemasterinterface)

# Set the language explicitly to C++
set_target_properties(gamemasterinterface PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB GAMEMASTERINTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "GAMEMASTERINTERFACE: ${GAMEMASTERINTERFACE}")

target_sources(gamemasterinterface PRIVATE ${GAMEMASTERINTERFACE})

# Include directories
target_include_directories(gamemasterinterface
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(gamemasterinterface PRIVATE
    logger
    orchestrator
    scenariohandler
    broker
    spdlog
)
