#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for Logger library

# Add the library
add_library(logger)

# Set the language explicitly to C++
set_target_properties(logger PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB LOGGER
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "LOGGER: ${LOGGER}")

target_sources(logger
    PRIVATE
    ${LOGGER}
)

# Include directories
target_include_directories(logger
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link the 3rdparty library
target_link_libraries(logger
    PRIVATE
    credentials
    curl
    orchestrator
    tomlplusplus::tomlplusplus
    spdlog
)
