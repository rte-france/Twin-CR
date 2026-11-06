#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

add_library(testing IncludeMocks.cpp)

target_include_directories(testing PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(testing PUBLIC
    dynawointerface
    orchestrator
    nlohmann_json::nlohmann_json
)
