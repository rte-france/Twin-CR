#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for AssetSimulator library

# Add the library
add_library(asset_simulator)

# Set the language explicitly to C++
set_target_properties(asset_simulator PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB ASSET_SIMULATOR_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "ASSET_SIMULATOR_SOURCES: ${ASSET_SIMULATOR_SOURCES}")

target_sources(asset_simulator PRIVATE ${ASSET_SIMULATOR_SOURCES})

# Include directories
target_include_directories(asset_simulator
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

add_subdirectory(AssetModels)

# Link the asset_simulator library
target_link_libraries(asset_simulator PRIVATE
    asset_models
    orchestrator
    informationflowmodel
    spdlog
    )
