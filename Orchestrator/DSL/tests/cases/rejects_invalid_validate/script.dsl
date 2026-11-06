// The other half: a validate() whose call would not survive being applied has to say so. Reporting at load time
// is the whole point of writing it, since the real call would fail the same way once its time came.
func isolate(breaker, feeder) {
  after 0 seconds, open switch $breaker;
  after 3 seconds, set load $feeder input "P" to 60;
}

after 2 seconds, validate(isolate("this_breaker_does_not_exist", "01_1"));
