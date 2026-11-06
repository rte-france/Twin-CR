// Deleting a function call that has not started yet has to take its children with it. A call stays Ready until
// its first child runs, so this is the window an operator is most likely to act in, and the one where deleting
// the parent alone would leave three events scheduled with nothing left to show they belong to anything.
func isolateFeeder(breaker, feeder) {
  after 0 seconds, open switch $breaker tagged "breaker_opened";
  after 3 seconds, decrease load $feeder input "P" by 15%;
  after "breaker_opened" is completed, set load $feeder input "P" to 80;
}

after 10 seconds, isolateFeeder("01_1_breaker", "01_1");
