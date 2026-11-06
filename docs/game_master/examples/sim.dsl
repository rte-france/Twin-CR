//
// Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
// See AUTHORS.md
// SPDX-License-Identifier: MPL-2.0
// This file is part of Twin-CR, a platform for real-time cyber-physical
// co-simulation of power systems.
//

// Example DSL file for power system simulation
// Compatible with IEEE 14-bus network
// Demonstrates time-based, condition-based, dependent events, and dynamic clusters
// Adjusted to avoid transformer and line parsing errors

// Set simulation parameters
set simulation duration to 60 seconds;
set time step to 1 seconds;

// Time-based events using valid IEEE14 load identifiers
at 5 seconds, increase load "_LOAD___2_EC" by 10% tagged "load_boost_start";
at 15 seconds, decrease load "_LOAD___2_EC" by 10% tagged "load_boost_end";

// Interval-based load increase with linear law
at [10 seconds, 20 seconds] with law "linear", increase load "LOAD   2" by 20%;

// Condition-based generator adjustment
when voltage at voltageLevel "_BUS____1_VL" > 1.05 pu, decrease generator "_GEN____1_SM" by 10% tagged "voltage_control";

// Dependent event
after "load_boost_start" is completed, increase generator "_GEN____2_SM" by 5% tagged "gen_followup";

// Fault application and clearing
at 12 seconds, apply fault at line "_BUS____1-BUS____2-1_AC";
at 18 seconds, clear fault at line "_BUS____1-BUS____2-1_AC";

// List-based load increase
at 3 seconds, increase load ["_LOAD___2_EC", "_LOAD___3_EC", "_LOAD___4_EC"] by 15%;

// Cluster-based generator decrease
at 25 seconds, decrease generator cluster "GenCluster" ["_GEN____2_SM", "_GEN____3_SM"] by 5%;

// Complex condition-based load adjustment
when (voltage at voltageLevel "_BUS____2_VL" < 0.95 pu and frequency at voltageLevel "_BUS____2_VL" > 50.1 Hz), increase load "_LOAD___2_EC" by 5%;

// Interval-based load decrease with step law
at [7 seconds, 14 seconds] with law "step", decrease load "LOAD   3" by 10%;

// Dependent event after voltage control
after "voltage_control" is completed, decrease load "_LOAD___3_EC" by 5% tagged "post_voltage_trim";

// Dynamic cluster with regex filter (all loads)
at 8 seconds, increase load dynamic cluster regex "_LOAD.*_EC" on load by 10%;

// Dynamic cluster with group_by filter (loads at specific voltage level)
at 22 seconds, decrease load dynamic cluster group by "voltage_level_id" "_BUS____2_VL" on load by 15%;

// Dynamic cluster with property filter (generators with high target power)
at 28 seconds, increase generator dynamic cluster where "target_p" > 50 MW on generator by 10%;

// Dynamic cluster with group_by substation (loads at specific substation)
at 30 seconds, increase load dynamic cluster group by "substation_id" "_BUS____4_SS" on load by 12%;

// Function DSL extension examples
func stagedLoadBoost(target, amount) {
  at +0 seconds, increase load target by amount% tagged "boost_start";
  at +5 seconds, decrease load target by amount% tagged "boost_end";
}

func recoverySequence(target, amount) {
  at +0 seconds, stagedLoadBoost(target, amount);
  after "boost_end" is completed, increase load target by 1%;
}

// Positional arguments
at 35 seconds, stagedLoadBoost("_LOAD___2_EC", 5);

// Named arguments with preflight verification
at 42 seconds, checkAndApply(
  stagedLoadBoost(target: "_LOAD___3_EC", amount: 3)
);

// Dependency-triggered function invocation
after "post_voltage_trim" is completed, recoverySequence("_LOAD___4_EC", 2);
