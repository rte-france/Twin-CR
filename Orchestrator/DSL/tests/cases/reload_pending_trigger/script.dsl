// Triggers that have not fired when the dump is taken. The 'when' still has to hold its condition tree and be
// watching the right measurement id; the 'after' still has to know which tag it waits on, and the tagged action
// it waits for only completes after the reload.
after 9 seconds, open switch "02_1_breaker" tagged "isolated";
when load "01_1" output "P" > 200, decrease load "01_1" input "P" by 10%;
after "isolated" is completed, set load "03_1" input "P" to 45;
