#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# CMake configuration for Broker library

# Add the library
add_library(broker)

# Set the language explicitly to C++
set_target_properties(broker PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB BROKER_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "BROKER_SOURCES: ${BROKER_SOURCES}")

target_sources(broker PRIVATE ${BROKER_SOURCES})

# Include directories
target_include_directories(broker
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Link the broker library
target_link_libraries(broker PUBLIC
    credentials
    orchestrator
    nats
    )

target_link_libraries(broker PRIVATE fmt::fmt)
target_compile_definitions(broker PRIVATE FMT_HEADER_ONLY=1)
