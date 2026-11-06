// Ported from the legacy functions example: parameterised functions, positional and named arguments, a tag scoped
// to one invocation, and the same function invoked twice without its tags colliding.
func isolateFeeder(breaker, feeder) {
  after 0 seconds, open switch $breaker tagged "breaker_opened";
  after 3 seconds, decrease load $feeder input "P" by 15%;
  after "breaker_opened" is completed, set load $feeder input "P" to 80;
}

func trimGeneration(feeder, amount) {
  after [0 seconds, 4 seconds] with law linear, decrease load $feeder input "P" by $amount%;
}

after 5 seconds, isolateFeeder("01_1_breaker", "01_1");
after 20 seconds, isolateFeeder(breaker: "02_1_breaker", feeder: "02_1");
after 30 seconds, trimGeneration("03_1", 12);
