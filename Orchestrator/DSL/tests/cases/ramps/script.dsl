// Both ramp kinds over an interval: a multiplier ramp (increase/decrease by a percentage) and a value ramp
// (set from X to Y). The per-tick payloads are what pin down the interpolation.
after [2 seconds, 6 seconds] with law linear, decrease load "01_1" input "P" by 20%;
after [10 seconds, 14 seconds] with law linear, set load "02_1" input "P" from 100 to 300;
