#
# Copyright (c) 2026, RTE (https://www.rte-france.com)
# See AUTHORS.md
# SPDX-License-Identifier: MPL-2.0
# This file is part of Twin-CR, a platform for real-time cyber-physical
# co-simulation of power systems.
#

add_executable(alarm_test AlarmDetectorTest.cpp)

target_link_libraries(alarm_test PRIVATE
    alarms
    spdlog
)

add_test(NAME alarms.detector COMMAND alarm_test)
set_tests_properties(alarms.detector PROPERTIES LABELS alarms)

# Same entry point as `make dsl-tests`: `make alarm-tests` builds and runs the alarm tests only
add_custom_target(alarm-tests
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure --label-regex alarms
    DEPENDS alarm_test
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Running the alarm tests"
)
