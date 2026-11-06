#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

# Add the library
add_library(dslwebinterface)

# Set the language explicitly to C++
set_target_properties(dslwebinterface PROPERTIES LINKER_LANGUAGE CXX)

# Add all source files from the directory and subdirectories
file(GLOB DSLWEBINTERFACE
    ${CMAKE_CURRENT_SOURCE_DIR}/*.cpp
)

# Display the list of source files
message(STATUS "DSLWEBINTERFACE: ${DSLWEBINTERFACE}")

target_sources(dslwebinterface PRIVATE ${DSLWEBINTERFACE})

# Include directories
target_include_directories(dslwebinterface
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Silences warnings from oatpp/oatpp-swagger's own headers
target_include_directories(dslwebinterface SYSTEM PRIVATE
    "${oatpp_SOURCE_DIR}/src"
    "${oatpp-swagger_SOURCE_DIR}/src"
)

# swagger-ui static assets are vendored inside the oatpp-swagger source tree (fully offline, no CDN).
# There are put in OATPP_SWAGGER_RES_PATH_BUILD (the FetchContent source dir).
# In docker, the source dir might not be available (not copied in multi-stage build), so the _INSTALL dir is used as fallback.
target_compile_definitions(dslwebinterface PRIVATE
    OATPP_SWAGGER_RES_PATH_BUILD="${oatpp-swagger_SOURCE_DIR}/res"
    OATPP_SWAGGER_RES_PATH_INSTALLED="${CMAKE_INSTALL_PREFIX}/share/oatpp-swagger/res"
)

install(DIRECTORY "${oatpp-swagger_SOURCE_DIR}/res/" DESTINATION share/oatpp-swagger/res)

target_link_libraries(dslwebinterface PRIVATE
    dsl
    credentials
    spdlog
    oatpp
    oatpp-swagger
)
