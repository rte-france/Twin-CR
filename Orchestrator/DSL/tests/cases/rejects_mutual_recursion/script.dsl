// The same thing one step removed: two functions that call each other. A check that only compares against the
// name being defined would miss this one.
func ping(breaker) {
  after 1 seconds, pong($breaker);
}

func pong(breaker) {
  after 1 seconds, ping($breaker);
}

after 2 seconds, ping("01_1_breaker");
