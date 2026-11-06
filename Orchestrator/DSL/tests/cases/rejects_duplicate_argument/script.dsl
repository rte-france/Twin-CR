// The same parameter named twice is the third way an argument can be silently discarded: one of the two values
// has to lose, and the caller is never told which.
func trip(breaker) {
  after 0 seconds, open switch $breaker;
}

after 2 seconds, trip(breaker: "01_1_breaker", breaker: "02_1_breaker");
