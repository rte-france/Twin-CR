#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for Launcher library

# Add the library
add_library(launcher)

# Set the language explicitly to C++
set_target_properties(launcher PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB LAUNCHER
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "LAUNCHER: ${LAUNCHER}")

target_sources(launcher PRIVATE ${LAUNCHER})

# Include directories
target_include_directories(launcher
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link the 3rdparty library
target_link_libraries(launcher
    PUBLIC
    asset_simulator
    broker
    credentials
    dsl
    dslwebinterface
    dynawointerface
    gamemasterinterface
    hmiinterface
    cycosiminterface
    # informationflowmodel
    logger
    processlauncher
    replay
    scenariohandler
    orchestrator
    spdlog
    tomlplusplus::tomlplusplus
)
