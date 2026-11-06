#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for CycosimInterface library

# Add the library
add_library(cycosiminterface)

# Set the language explicitly to C++
set_target_properties(cycosiminterface PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB CYCOSIMINTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "CYCOSIMINTERFACE: ${CYCOSIMINTERFACE}")

target_sources(cycosiminterface PRIVATE ${CYCOSIMINTERFACE})

# Include directories
target_include_directories(cycosiminterface
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../
)
# cppzmq_INCLUDE_DIR must be marked as SYSTEM to avoid shadowing fetched dependencies
target_include_directories(cycosiminterface SYSTEM PUBLIC ${cppzmq_INCLUDE_DIR})

target_link_libraries(cycosiminterface PRIVATE
    informationflowmodel
    orchestrator
    spdlog
    ${ZMQ_LIBRARY}
)
