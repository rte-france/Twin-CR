// The other ramp kind across a dump/reload. A value ramp interpolates an absolute setpoint rather than composing
// multipliers, so unlike the multiplier ramp it emits at the interval start too, and it has no accumulated state
// to carry: the restored interval and endpoints are enough to keep the line straight.
after [4 seconds, 12 seconds] with law linear, set load "01_1" input "P" from 100 to 300;
