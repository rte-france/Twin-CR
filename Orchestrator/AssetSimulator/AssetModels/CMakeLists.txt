#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for AssetModels library

# Add the library
add_library(asset_models)

# Set the language explicitly to C++
set_target_properties(asset_models PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB ASSET_MODELS_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "ASSET_MODELS_SOURCES: ${ASSET_MODELS_SOURCES}")

target_sources(asset_models PRIVATE ${ASSET_MODELS_SOURCES})

# Include directories
target_include_directories(asset_models
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link the asset_models library
target_link_libraries(asset_models PRIVATE
    orchestrator
    informationflowmodel
    )
