#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

cmake_minimum_required(VERSION 3.10)

# Fetch 3rd parties (before setting warning flags to avoid spurious warnings from external libraries)
include(${CMAKE_CURRENT_SOURCE_DIR}/deps/CMakeLists.txt)

project(orchestrator_project)

# Set compile flags AFTER fetching dependencies to avoid warnings from them
set (CMAKE_CXX_FLAGS "-O3 -Wall -Wextra -pedantic -pthread")

# -O3
# -fsanitize=thread -g -O1
# -fsanitize=address -g -O1

# set(CMAKE_CXX_CLANG_TIDY "clang-tidy;-checks=\
#   clang-analyzer-*,\
#   bugprone-*,\
#   modernize-*,\
#   performance-*,\
#   readability-*,\
#   -modernize-pass-by-value,\
#   -modernize-use-trailing-return-type,\
#   -performance-avoid-endl,\
#   -performance-unnecessary-value-param,\
#   -readability-identifier-length,\
#   -readability-braces-around-statements,\
#   -bugprone-easily-swappable-parameters,\
#   ;-header-filter=^${CMAKE_SOURCE_DIR}/src/"
#   )

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)  # Generates a compile_commands.json for clangd

option(ORCHESTRATOR_BUILD_TESTS "Build the orchestrator test executables and register them with CTest" OFF)
if(ORCHESTRATOR_BUILD_TESTS)
    enable_testing()
endif()

find_path(cppzmq_INCLUDE_DIR zmq.hpp REQUIRED)
find_library(ZMQ_LIBRARY zmq REQUIRED)

message(STATUS "Found cppzmq:" ${cppzmq_INCLUDE_DIR})
message(STATUS "Found ZMQ:" ${ZMQ_LIBRARY})

# Include subdirectories
add_subdirectory(AssetSimulator)
add_subdirectory(Broker)
add_subdirectory(Credentials)
add_subdirectory(CycosimInterface)
if(ORCHESTRATOR_BUILD_TESTS)
    add_subdirectory(testing)  # before DSL, whose tests link it
endif()
add_subdirectory(DSL)
add_subdirectory(DSLWebInterface)
add_subdirectory(DynawoInterface)
add_subdirectory(GameMasterInterface)
add_subdirectory(HmiInterface)
add_subdirectory(InformationFlowModel)
add_subdirectory(Launcher)
add_subdirectory(Logger)
add_subdirectory(Orchestrator)
add_subdirectory(ProcessLauncher)
add_subdirectory(Replay)
add_subdirectory(ScenarioHandler)

# Add the main executable
add_executable(orchestrator_project main.cpp )
set_target_properties(${PROJECT_NAME} PROPERTIES OUTPUT_NAME "orchestrator_exec")

# cppzmq_INCLUDE_DIR must be marked as SYSTEM to avoid shadowing fetched dependencies
target_include_directories(orchestrator_project SYSTEM PUBLIC ${cppzmq_INCLUDE_DIR})

# Link the main executable with all libraries discovered in subdirectories
target_link_libraries(orchestrator_project PUBLIC
    launcher
    tomlplusplus::tomlplusplus
)
target_compile_definitions(orchestrator_project PRIVATE MI_MALLOC_OVERRIDE=1)

install (TARGETS orchestrator_project RUNTIME DESTINATION bin)
