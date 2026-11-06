#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for HmiInterface library

# Add the library
add_library(hmiinterface)

# Set the language explicitly to C++
set_target_properties(hmiinterface PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB HMIINTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "HMIINTERFACE: ${HMIINTERFACE}")

target_sources(hmiinterface PRIVATE ${HMIINTERFACE})

# Include directories
target_include_directories(hmiinterface
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(hmiinterface PRIVATE
    broker
    orchestrator
    informationflowmodel
    logger
    scenariohandler
    mimalloc
)
