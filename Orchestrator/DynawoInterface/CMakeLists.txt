#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for DynawoInterface library

# Add the library
add_library(dynawointerface)

# Set the language explicitly to C++
set_target_properties(dynawointerface PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB_RECURSE DYNOWOINTERFACE_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "DYNOWOINTERFACE_SOURCES: ${DYNOWOINTERFACE_SOURCES}")

target_sources(dynawointerface PRIVATE ${DYNOWOINTERFACE_SOURCES})

# Include directories
target_include_directories(dynawointerface
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)
# cppzmq_INCLUDE_DIR must be marked as SYSTEM to avoid shadowing fetched dependencies
target_include_directories(dynawointerface SYSTEM PUBLIC ${cppzmq_INCLUDE_DIR})

# Link dynawointerface with the DynawoHandlers library
target_link_libraries(dynawointerface PUBLIC
    informationflowmodel
    logger
    orchestrator
    processlauncher
    ${ZMQ_LIBRARY}
    mimalloc
    spdlog
)
