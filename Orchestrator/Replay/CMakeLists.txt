#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for Replay library

# Add the library
add_library(replay)

# Set the language explicitly to C++
set_target_properties(replay PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB REPLAY_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "REPLAY_SOURCES: ${REPLAY_SOURCES}")

target_sources(replay
    PRIVATE
    ${REPLAY_SOURCES}
)

# Include directories
target_include_directories(replay
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link the replay library
target_link_libraries(replay PRIVATE
    credentials
    logger
    orchestrator
    spdlog
    )
