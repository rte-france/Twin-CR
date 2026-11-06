//
// Copyright (c) 2026, RTE (https://www.rte-france.com)
// See AUTHORS.md
// SPDX-License-Identifier: MPL-2.0
// This file is part of Twin-CR, a platform for real-time cyber-physical
// co-simulation of power systems.
//

// Example DSL file to exercise function support on the Nordic scenario.
// Covered concepts:
// - simulation-scoped function definitions
// - forward references
// - positional and named arguments
// - nested function calls
// - relative timings inside function bodies
// - local tags inside functions
// - verified invocation through checkAndApply(...)
// - IFM / network-characteristics helper functions
// - regex-based dynamic clusters
// - interval-based ramps

set simulation duration to 600 seconds;
set time step to 1 second;

// Forward reference + positional arguments.
at 60 seconds, plannedConsignation(
  "L4032-4044_breaker1",
  "L4032-4044_breaker2"
);

// Named arguments + checkAndApply(...) on a pure switching sequence.
at 150 seconds, checkAndApply(
  plannedConsignation(
    breaker: "L4041-4044_breaker1",
    coupler: "L4032-4044_breaker2"
  )
);

// Simple direct invocation with an explicit trigger time.
at 5 seconds, couplerPulse("L4032-4044_breaker2");

// Nested function call + local tag isolation across repeated invocations.
at 260 seconds, coordinatedRestoration(
  target: "L4032-4044_breaker2",
  backup_breaker: "L4032-4044_breaker1"
);

// IFM-style communication blackout / recovery helpers.
at 320 seconds, s4032RtuBlackout();
at 360 seconds, s4032RtuRecover();

// Regex + interval function with parameterized bounds and amount.
at 420 seconds, regexLoadRelief(
  amount: 5,
  start_offset: 0,
  end_offset: 5
);

// Interval-based generator ramp helper.
at 470 seconds, stagedGeneratorCurtailment(12);

// Plain existing commands kept in the same file to verify legacy DSL still works
// alongside function-based authoring.
at 520 seconds, open switch "L4032-4044_breaker1" tagged "legacy_breaker_open";
after "legacy_breaker_open" is completed, close switch "L4032-4044_breaker1";

at 540 seconds, change network characteristics link from "S_4032" to "SCADA", drop fixed true;
at 540 seconds, change network characteristics link from "SCADA" to "S_4032", drop fixed true;
at 550 seconds, change network characteristics link from "S_4032" to "SCADA", drop fixed false;
at 550 seconds, change network characteristics link from "SCADA" to "S_4032", drop fixed false;

at [560 seconds, 565 seconds] with law "linear", decrease load dynamic cluster regex "^Y.*(T|Y|TR).[12].$" on load by 5%;
at [575 seconds, 585 seconds] with law "linear", decrease generator cluster "Gen1" [ "g01" ] by 10%;
at [580 seconds, 590 seconds] with law "linear", decrease generator cluster "Gen2" [ "g02" ] by 10%;

func plannedConsignation(breaker, coupler) {
  at +0 seconds, open switch breaker tagged "breaker_opened";
  at +20 seconds, couplerPulse(coupler);
}

func couplerPulse(target) {
  at +0 seconds, open switch target tagged "pulse_opened";
  after "pulse_opened" is completed, close switch target;
}

func coordinatedRestoration(target, backup_breaker) {
  at +0 seconds, open switch backup_breaker tagged "backup_opened";
  at +10 seconds, couplerPulse(target);
  after "backup_opened" is completed, close switch backup_breaker;
}

func s4032RtuBlackout() {
  at +0 seconds, change network characteristics link from "S_4032" to "SCADA", drop fixed true;
  at +0 seconds, change network characteristics link from "SCADA" to "S_4032", drop fixed true;
}

func s4032RtuRecover() {
  at +0 seconds, change network characteristics link from "S_4032" to "SCADA", drop fixed false;
  at +0 seconds, change network characteristics link from "SCADA" to "S_4032", drop fixed false;
}

func regexLoadRelief(amount, start_offset, end_offset) {
  at [start_offset seconds, end_offset seconds] with law "linear", decrease load dynamic cluster regex "^Y.*(T|Y|TR).[12].$" on load by amount%;
}

func stagedGeneratorCurtailment(amount) {
  at [+0 seconds, +10 seconds] with law "linear", decrease generator cluster "Gen1" [ "g01" ] by amount%;
  at [+5 seconds, +15 seconds] with law "linear", decrease generator cluster "Gen2" [ "g02" ] by amount%;
}
