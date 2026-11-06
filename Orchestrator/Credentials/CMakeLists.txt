#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Add the library
add_library(credentials)

# Set the language explicitly to C++
set_target_properties(credentials PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB CREDENTIALS
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "CREDENTIALS: ${CREDENTIALS}")

target_sources(credentials PRIVATE ${CREDENTIALS})

# Include directories
target_include_directories(credentials
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(credentials PRIVATE
    spdlog
)
