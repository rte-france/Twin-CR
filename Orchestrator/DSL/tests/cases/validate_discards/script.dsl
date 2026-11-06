// validate() expands a call and checks every event it would create against the network, then throws the batch
// away. Making the same call for real further down is what shows the difference: nothing lands at the time the
// validate was scheduled for, and everything lands at the time the real call was.
func isolate(breaker, feeder) {
  after 0 seconds, open switch $breaker;
  after 3 seconds, set load $feeder input "P" to 60;
}

after 2 seconds, validate(isolate("01_1_breaker", "01_1"));
after 8 seconds, isolate("01_1_breaker", "01_1");
