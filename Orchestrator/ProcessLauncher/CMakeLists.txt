#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for ProcessLauncher library

# Add the library
add_library(processlauncher)

# Set the language explicitly to C++
set_target_properties(processlauncher PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB_RECURSE PROCESSLAUNCHER_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "PROCESSLAUNCHER_SOURCES: ${PROCESSLAUNCHER_SOURCES}")

target_sources(processlauncher PRIVATE ${PROCESSLAUNCHER_SOURCES})

# Include directories
target_include_directories(processlauncher
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${libsubprocess_SOURCE_DIR}
)

# Link the processlauncher library
target_link_libraries(processlauncher PUBLIC
    spdlog
)
