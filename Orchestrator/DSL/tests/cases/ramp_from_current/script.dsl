// Without 'from', a value ramp starts from the element's current measured value instead of a written number.
after [5 seconds, 9 seconds], set load "02_1" input "P" to 300;

// The same, but no measurement has arrived when the interval opens: the ramp applies nothing until one does,
// then picks up at the point the interval has already reached rather than restarting.
// Both ramps cross the dump/reload at 6, one with its start read and one still waiting for it.
after [5 seconds, 9 seconds], set load "03_1" input "P" to 300;

// 04_1 is never measured at all. The ramp applies nothing while the interval runs, then writes its final value
// at the end rather than being dropped: the endpoint is the one value it is sure of.
after [5 seconds, 9 seconds], set load "04_1" input "P" to 300;

// An interval shorter than the period is the same case: there is no tick inside it for a measurement to land on.
after [12 seconds, 12.001 seconds], set load "05_1" input "P" to 400;
