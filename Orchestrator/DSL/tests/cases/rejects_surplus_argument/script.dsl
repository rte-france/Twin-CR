// A call passing more arguments than the function declares has to be reported rather than quietly truncated.
// Since this is the configured dsl_file, the rejection propagates out of the engine's constructor and the run
// never starts, so the action on the line above it is not applied either.
func trip(breaker) {
  after 0 seconds, open switch $breaker;
}

after 2 seconds, trip("01_1_breaker");
after 5 seconds, trip("02_1_breaker", "03_1_breaker");
