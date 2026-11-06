#
# Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

cmake_minimum_required(VERSION 3.10)
# Set C++ standard
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_FLAGS "-O3")

project(orchestrator_deps)

if(POLICY CMP0135)
	cmake_policy(SET CMP0135 NEW)
	set(CMAKE_POLICY_DEFAULT_CMP0135 NEW)
endif()

include(FetchContent)
FetchContent_Declare(
  libsubprocess
  GIT_REPOSITORY https://github.com/sheredom/subprocess.h.git
  GIT_TAG        b49c56e9fe214488493021017bf3954b91c7c1f5  # Latest as of 17 April 2026 (last updated 2y ago)
)
FetchContent_MakeAvailable(libsubprocess)

FetchContent_Declare(
  spdlog
  GIT_REPOSITORY https://github.com/gabime/spdlog.git
  GIT_TAG v1.15.3
)
set(SPDLOG_BUILD_EXAMPLE  OFF CACHE BOOL "Build example" FORCE)
set(SPDLOG_BUILD_TESTS  OFF CACHE BOOL "Build tests" FORCE)
set(SPDLOG_USE_STD_FORMAT OFF CACHE BOOL "Use std::format" FORCE)
FetchContent_MakeAvailable(spdlog)

FetchContent_Declare(
        graaflib
        GIT_REPOSITORY https://github.com/bobluppes/graaf.git
        GIT_TAG 8b0701d56662ffa71cf312b970d7ee89b1240e69  # Pin before breaking https://github.com/bobluppes/graaf/pull/306
)
set(SKIP_TESTS ON)
set(SKIP_BENCHMARKS ON)
set(SKIP_EXAMPLES ON)
FetchContent_MakeAvailable(graaflib)

FetchContent_Declare(json URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz)
FetchContent_MakeAvailable(json)

FetchContent_Declare(pugixml URL https://github.com/zeux/pugixml/releases/download/v1.15/pugixml-1.15.tar.gz)
FetchContent_MakeAvailable(pugixml)

FetchContent_Declare(
    tomlplusplus
    GIT_REPOSITORY https://github.com/marzer/tomlplusplus.git
    GIT_TAG v3.4.0
)
FetchContent_MakeAvailable(tomlplusplus)

FetchContent_Declare(
  mimalloc
  GIT_REPOSITORY https://github.com/microsoft/mimalloc.git
  GIT_TAG v2.1.2
)
set(MI_BUILD_SHARED ON CACHE BOOL "" FORCE)
set(MI_INSTALL OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(mimalloc)

set(SER20_BUILD_SANDBOX OFF CACHE BOOL "" FORCE)
FetchContent_Declare(
  ser20
  GIT_REPOSITORY https://github.com/royjacobson/ser20.git
  GIT_TAG        56f17ed05fe7e9f4c5fdb33c6fff9d1063bb5ff7  # v0.9.1
)
if(POLICY CMP0167)
	cmake_policy(SET CMP0167 NEW)
	set(CMAKE_POLICY_DEFAULT_CMP0167 NEW)
endif()
FetchContent_MakeAvailable(ser20)

FetchContent_Declare(
  nats
  GIT_REPOSITORY https://github.com/nats-io/nats.c.git
  GIT_TAG        v3.10.1
)
# Disable unused components
set(NATS_BUILD_STREAMING OFF CACHE BOOL "Disable streaming" FORCE)
set(NATS_BUILD_TESTS OFF CACHE BOOL "Disable tests" FORCE)
set(NATS_BUILD_EXAMPLES OFF CACHE BOOL "Disable examples" FORCE)

FetchContent_MakeAvailable(nats)

FetchContent_Declare(
  fmt
  GIT_REPOSITORY https://github.com/fmtlib/fmt.git
  GIT_TAG        11.2.0
)
FetchContent_MakeAvailable(fmt)

set(ANTLR4_TAG "4.13.2")
FetchContent_Declare(
  antlr4_runtime
  GIT_REPOSITORY https://github.com/antlr/antlr4.git
  GIT_TAG        ${ANTLR4_TAG}
  GIT_SUBMODULES ""          # don't recurse - only the C++ runtime is needed
  SOURCE_SUBDIR  runtime/Cpp
)
set(ANTLR4_INSTALL        OFF CACHE BOOL "" FORCE)
set(WITH_DEMO             OFF CACHE BOOL "" FORCE)
set(WITH_STATIC_CRT       OFF CACHE BOOL "" FORCE)
set(ANTLR_BUILD_CPP_TESTS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(antlr4_runtime)

FetchContent_Declare(
  antlr4_c3
  GIT_REPOSITORY https://github.com/mike-lischke/antlr4-c3.git
  GIT_TAG        v3.4.3
)
FetchContent_MakeAvailable(antlr4_c3)

# ─── oatpp + oatpp-swagger (used by DSLWebInterface for the DSL HTTP/REST API and its auto-generated OpenAPI docs) ───
set(OATPP_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(OATPP_INSTALL     OFF CACHE BOOL "" FORCE)
FetchContent_Declare(
  oatpp
  GIT_REPOSITORY https://github.com/oatpp/oatpp.git
  GIT_TAG        1.3.0
)
FetchContent_MakeAvailable(oatpp)

FetchContent_Declare(
  oatpp-swagger
  GIT_REPOSITORY https://github.com/oatpp/oatpp-swagger.git
  GIT_TAG        1.3.0
)
# oatpp-swagger's own CMakeLists.txt defaults to find_package(oatpp) (expecting an installed package); CUSTOM
# skips both that and its own redundant ExternalProject fetch, relying on the oatpp::oatpp target already made
# available just above in this same configure run. OATPP_DIR_SRC still needs pointing at oatpp's headers directly
# (its src/CMakeLists.txt uses it in target_include_directories regardless of mode).
set(OATPP_MODULES_LOCATION "CUSTOM" CACHE STRING "" FORCE)
FetchContent_GetProperties(oatpp)
set(OATPP_DIR_SRC "${oatpp_SOURCE_DIR}/src" CACHE STRING "" FORCE)
FetchContent_MakeAvailable(oatpp-swagger)
