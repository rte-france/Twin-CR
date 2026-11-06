// A function call whose work all lands after a dump/reload. The call is made at 3 s and the engine is dumped at
// 7.5 s, so by then the invocation exists only as committed events: three child ids, their scheduled times, and
// a tag qualified to this invocation. Everything below therefore has to come back out of the dump.
func stagedIsolation(breaker, feeder) {
  after 6 seconds, open switch $breaker tagged "breaker_opened";
  after 8 seconds, decrease load $feeder input "P" by 10%;
  after "breaker_opened" is completed, set load $feeder input "P" to 60;
}

after 3 seconds, stagedIsolation("01_1_breaker", "01_1");
