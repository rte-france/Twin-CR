#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for InformationFlowModel library

# Add the library
add_library(informationflowmodel)

# Set the language explicitly to C++
set_target_properties(informationflowmodel PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB INFORMATIONFLOWMODEL
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "INFORMATIONFLOWMODEL: ${INFORMATIONFLOWMODEL}")

target_sources(informationflowmodel PRIVATE ${INFORMATIONFLOWMODEL})

# Include directories
target_include_directories(informationflowmodel
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${graaflib_SOURCE_DIR}/include
)

# Link the 3rdparty library
target_link_libraries(informationflowmodel
    PUBLIC
    broker
    logger
    orchestrator
    mimalloc
    ser20
    spdlog
)
