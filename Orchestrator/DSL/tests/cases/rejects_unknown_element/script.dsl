// The engine must refuse a script naming an element the network does not have, and refuse it at load time rather
// than when the action comes due. Since this is the configured dsl_file, the rejection propagates out of the
// engine's constructor and the run never starts, so nothing is applied at all.
after 2 seconds, open switch "01_1_breaker";
after 4 seconds, open switch "this_breaker_does_not_exist";
