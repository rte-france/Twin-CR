// A named argument matching no parameter has to be reported. Here both parameters are already satisfied
// positionally, so nothing downstream notices that the misspelled one was never used.
func isolate(breaker, feeder) {
  after 0 seconds, open switch $breaker;
  after 1 second, set load $feeder input "P" to 80;
}

after 2 seconds, isolate("01_1_breaker", "01_1", feder: "02_1");
