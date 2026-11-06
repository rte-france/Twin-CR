//
// Copyright (c) 2026, RTE (https://www.rte-france.com)
// See AUTHORS.md
// SPDX-License-Identifier: MPL-2.0
// This file is part of Twin-CR, a platform for real-time cyber-physical
// co-simulation of power systems.
//

// Example DSL file to exercise function support on the Nordic scenario.
// Covered concepts:
// - function definitions, which precede their call sites
// - positional and named arguments
// - nested function calls
// - relative timings inside function bodies
// - local tags inside functions
// - verified invocation through validate(...)
// - IFM / network-characteristics helper functions
// - regex-based clusters
// - interval-based ramps

func couplerPulse(coupler) {
  after 0 seconds, open switch $coupler tagged "pulse_opened";
  after "pulse_opened" is completed, close switch $coupler;
}

func plannedConsignation(breaker, coupler) {
  after 0 seconds, open switch $breaker tagged "breaker_opened";
  after 20 seconds, couplerPulse($coupler);
}

func coordinatedRestoration(target, backup_breaker) {
  after 0 seconds, open switch $backup_breaker tagged "backup_opened";
  after 10 seconds, couplerPulse($target);
  after "backup_opened" is completed, close switch $backup_breaker;
}

func s4032RtuBlackout() {
  after 0 seconds, change network characteristics link from "S_4032" to "SCADA", drop fixed true;
  after 0 seconds, change network characteristics link from "SCADA" to "S_4032", drop fixed true;
}

func s4032RtuRecover() {
  after 0 seconds, change network characteristics link from "S_4032" to "SCADA", drop fixed false;
  after 0 seconds, change network characteristics link from "SCADA" to "S_4032", drop fixed false;
}

func regexLoadRelief(amount, start_offset, end_offset) {
  after [$start_offset seconds, $end_offset seconds] with law linear,
     decrease load cluster regex "^4[0-9]_1$" on load input "P" by $amount%;
}

func stagedLoadCurtailment(amount) {
  after [0 seconds, 10 seconds] with law linear, decrease load cluster "Group1" [ "01_1" ] input "P" by $amount%;
  after [5 seconds, 15 seconds] with law linear, decrease load cluster "Group2" [ "02_1" ] input "P" by $amount%;
}

// Positional arguments.
after 60 seconds, plannedConsignation(
  "L4032-4044_breaker1",
  "L4032-4044_breaker2"
);

// Named arguments + validate(...): the call is resolved and checked at load, and nothing is applied.
after 150 seconds, validate(
  plannedConsignation(
    breaker: "L4041-4044_breaker1",
    coupler: "L4041-4044_breaker2"
  )
);

// Simple direct invocation with an explicit trigger time.
after 5 seconds, couplerPulse("L4032-4044_breaker2");

// Nested function call + local tag isolation across repeated invocations.
after 260 seconds, coordinatedRestoration(
  target: "L4041-4044_breaker2",
  backup_breaker: "L4041-4044_breaker1"
);

// IFM-style communication blackout / recovery helpers.
after 320 seconds, s4032RtuBlackout();
after 360 seconds, s4032RtuRecover();

// Regex + interval function with parameterized bounds and amount.
after 420 seconds, regexLoadRelief(
  amount: 5,
  start_offset: 0,
  end_offset: 5
);

// Interval-based load ramp helper.
after 470 seconds, stagedLoadCurtailment(12);

// Plain statements kept in the same file to verify direct authoring still works
// alongside function-based authoring.
after 520 seconds, open switch "L4032-4044_breaker1" tagged "direct_breaker_open";
after "direct_breaker_open" is completed, close switch "L4032-4044_breaker1";

after 540 seconds, change network characteristics link from "S_4031" to "SCADA", drop fixed true;
after 540 seconds, change network characteristics link from "SCADA" to "S_4031", drop fixed true;
after 550 seconds, change network characteristics link from "S_4031" to "SCADA", drop fixed false;
after 550 seconds, change network characteristics link from "SCADA" to "S_4031", drop fixed false;

after [560 seconds, 565 seconds] with law linear, decrease load cluster regex "^1[0-9]_1$" on load input "P" by 5%;
after [575 seconds, 585 seconds] with law linear, decrease load cluster "Group3" [ "03_1" ] input "P" by 10%;
after [580 seconds, 590 seconds] with law linear, decrease load cluster "Group4" [ "04_1" ] input "P" by 10%;
