/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

/*
 * The mocks are header-only, so this exists to compile them. This is mainly to add this directory in the compile_commands.json
 * to help clangd to correctly resolve includes
 */

#include "ExampleDynawoInterface.h"
#include "RecordingScenarioHandler.h"
#include "TmpDirClickHouseLogger.h"

#include <type_traits>

namespace orchestrator_testing {

// Silence unused warnings
static_assert(std::is_base_of_v<DynawoInterfaceInterface, ExampleDynawoInterface>);
static_assert(std::is_base_of_v<ScenarioHandlerInterface, RecordingScenarioHandler>);
static_assert(std::is_base_of_v<ClickHouseLoggerInterface, TmpDirClickHouseLogger>);

// Keeps the object file from being empty
bool linked() {
    return true;
}

}  // namespace orchestrator_testing
