//
// Copyright (c) 2026, RTE (https://www.rte-france.com)
// See AUTHORS.md
// SPDX-License-Identifier: MPL-2.0
// This file is part of Twin-CR, a platform for real-time cyber-physical
// co-simulation of power systems.
//

set simulation duration to 200 seconds;
set time step to 2 seconds;  // Temporary workaround non-determinism of the DSL server when using small time steps (orchestrator might receive the actions with more than 100ms delay), by publishing the t=5.1s switching actions at t=4s instead of t=5s to avoid delayed implementation

// Time-based events
at 5.1 seconds, open switch "L4032-4044_breaker1";
at 5.1 seconds, open switch "L4032-4044_breaker2";
