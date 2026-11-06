// A function that calls itself can never terminate: the language has no conditional and no loop, so there is
// nothing to end the expansion. It has to be reported at load time, not run until the stack gives out.
func trip(breaker) {
  after 1 seconds, trip($breaker);
}

after 2 seconds, trip("01_1_breaker");
