// Conditional triggers driven by injected measurements. 'when' fires once and completes; 'when_rearming' fires
// again after the condition has gone false in between.
when load "01_1" output "P" > 200, open switch "01_1_breaker" tagged "overload_trip";
when_rearming load "02_1" output "P" > 150, decrease load "02_1" input "P" by 5%;
