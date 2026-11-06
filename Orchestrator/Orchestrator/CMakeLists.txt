#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for Orchestrator library

# Add the library
add_library(orchestrator)

# Set the language explicitly to C++
set_target_properties(orchestrator PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB ORCHESTRATOR_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "ORCHESTRATOR_SOURCES: ${ORCHESTRATOR_SOURCES}")

target_sources(orchestrator
    PRIVATE
    ${ORCHESTRATOR_SOURCES}
)

# Include directories
target_include_directories(orchestrator
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link the orchestrator library
target_link_libraries(orchestrator PUBLIC
    Graaf::Graaf
    nlohmann_json::nlohmann_json
    pugixml
    tomlplusplus::tomlplusplus
    ser20
    spdlog
    )

target_link_libraries(orchestrator PUBLIC fmt::fmt)
target_compile_definitions(orchestrator PUBLIC FMT_HEADER_ONLY=1)
